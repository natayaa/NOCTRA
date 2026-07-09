from uuid import UUID
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, delete, update
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from core.constants import InventoryStatus, StockMovementType
from core.exceptions import NotFoundError
from .models import (
    InventoryItem,
    InventoryMaterialUsage,
    InventoryStockMovement,
    ProjectWorkshopTask,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    StockAlert,
    StockOpname,
    InventoryValuation,
)


class InventoryRepository(BaseRepository[InventoryItem]):
    """Repository untuk Inventory Item."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InventoryItem)

    # ==================== READ ====================

    async def get_by_sku(self, sku: str) -> Optional[InventoryItem]:
        """Get item by SKU."""
        stmt = select(InventoryItem).where(InventoryItem.sku == sku)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_barcode(self, barcode: str) -> Optional[InventoryItem]:
        """Get item by barcode."""
        stmt = select(InventoryItem).where(InventoryItem.barcode == barcode)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, item_id: UUID) -> Optional[InventoryItem]:
        """Get item with all related data."""
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.id == item_id)
            .options(
                selectinload(InventoryItem.supplier),
                selectinload(InventoryItem.material_usages),
                selectinload(InventoryItem.stock_movements),
                selectinload(InventoryItem.alerts),
                selectinload(InventoryItem.opnames),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        low_stock_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[InventoryItem], int]:
        """List items with filters."""
        stmt = select(InventoryItem)
        count_stmt = select(func.count()).select_from(InventoryItem)

        filters = []
        if category:
            filters.append(InventoryItem.category == category)
        if status:
            filters.append(InventoryItem.status == status)
        if low_stock_only:
            filters.append(InventoryItem.current_stock <=
                           InventoryItem.min_stock_threshold)
        if search:
            filters.append(
                or_(
                    InventoryItem.name.ilike(f"%{search}%"),
                    InventoryItem.sku.ilike(f"%{search}%"),
                    InventoryItem.barcode.ilike(f"%{search}%"),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.options(selectinload(InventoryItem.supplier))
        stmt = stmt.order_by(InventoryItem.name).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return items, total

    async def get_by_category(self, category: str) -> List[InventoryItem]:
        """Get items by category."""
        stmt = select(InventoryItem).where(InventoryItem.category == category)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_low_stock_items(self) -> List[InventoryItem]:
        """Get all low stock items."""
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.current_stock <= InventoryItem.min_stock_threshold)
            .order_by(InventoryItem.current_stock)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_out_of_stock_items(self) -> List[InventoryItem]:
        """Get all out of stock items."""
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.current_stock <= 0)
            .order_by(InventoryItem.name)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        stmt = select(InventoryItem.category).distinct().order_by(
            InventoryItem.category)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ==================== UPDATE ====================

    async def update_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        movement_type: str,
        reference_type: str,
        reference_id: Optional[UUID] = None,
        note: Optional[str] = None,
        performed_by: Optional[str] = None
    ) -> Optional[InventoryItem]:
        """Update item stock with movement tracking."""
        item = await self.get(item_id)
        if not item:
            return None

        previous_stock = item.current_stock

        if movement_type in [StockMovementType.PURCHASE, StockMovementType.RETURN]:
            item.current_stock += quantity
        elif movement_type in [StockMovementType.SALE, StockMovementType.USAGE, StockMovementType.WASTE]:
            if item.current_stock < quantity:
                raise ValueError(
                    f"Insufficient stock. Current: {item.current_stock}, Required: {quantity}"
                )
            item.current_stock -= quantity
        elif movement_type == StockMovementType.ADJUSTMENT:
            item.current_stock = quantity
        else:
            raise ValueError(f"Invalid movement type: {movement_type}")

        # Update status if out of stock
        if item.current_stock <= 0:
            item.status = InventoryStatus.OUT_OF_STOCK
        elif item.status == InventoryStatus.OUT_OF_STOCK:
            item.status = InventoryStatus.ACTIVE

        # Update available stock
        item.available_stock = item.current_stock - item.reserved_stock

        # Create stock movement record
        movement = InventoryStockMovement(
            item_id=item_id,
            type=movement_type,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=item.current_stock,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
            performed_by=performed_by or "system"
        )
        self.db.add(movement)

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def reserve_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID
    ) -> Optional[InventoryItem]:
        """Reserve stock for a project or job."""
        item = await self.get(item_id)
        if not item:
            return None

        available = item.current_stock - item.reserved_stock
        if available < quantity:
            raise ValueError(
                f"Insufficient available stock. Available: {available}, Required: {quantity}"
            )

        item.reserved_stock += quantity
        item.available_stock = item.current_stock - item.reserved_stock

        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.RESERVATION,
            quantity=quantity,
            previous_stock=item.current_stock,
            new_stock=item.current_stock,
            reference_type=reference_type,
            reference_id=reference_id,
            note="Stock reserved",
            performed_by="system"
        )
        self.db.add(movement)

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def release_reserved_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID
    ) -> Optional[InventoryItem]:
        """Release reserved stock."""
        item = await self.get(item_id)
        if not item:
            return None

        if item.reserved_stock < quantity:
            raise ValueError(
                f"Cannot release more than reserved. Reserved: {item.reserved_stock}, Requested: {quantity}"
            )

        item.reserved_stock -= quantity
        item.available_stock = item.current_stock - item.reserved_stock

        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.RELEASE,
            quantity=quantity,
            previous_stock=item.current_stock,
            new_stock=item.current_stock,
            reference_type=reference_type,
            reference_id=reference_id,
            note="Stock reservation released",
            performed_by="system"
        )
        self.db.add(movement)

        await self.db.flush()
        await self.db.refresh(item)
        return item

    # ==================== STATISTICS ====================

    async def get_statistics(self) -> dict:
        """Get inventory statistics."""
        total_stmt = select(func.count()).select_from(InventoryItem)
        total = await self.db.scalar(total_stmt) or 0

        status_stmt = select(
            InventoryItem.status,
            func.count().label('count')
        ).group_by(InventoryItem.status)
        result_status = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in result_status}

        category_stmt = select(
            InventoryItem.category,
            func.count().label('count'),
            func.sum(InventoryItem.current_stock).label('total_stock')
        ).group_by(InventoryItem.category)
        result_category = await self.db.execute(category_stmt)
        category_stats = {
            row.category: {"count": row.count, "total_stock": row.total_stock}
            for row in result_category
        }

        value_stmt = select(
            func.sum(InventoryItem.current_stock * InventoryItem.cost_price)
        )
        total_value = await self.db.scalar(value_stmt) or Decimal(0)

        low_count_stmt = select(func.count()).select_from(InventoryItem).where(
            InventoryItem.current_stock <= InventoryItem.min_stock_threshold
        )
        low_count = await self.db.scalar(low_count_stmt) or 0

        out_count_stmt = select(func.count()).select_from(InventoryItem).where(
            InventoryItem.current_stock <= 0
        )
        out_count = await self.db.scalar(out_count_stmt) or 0

        return {
            "total_items": total,
            "by_status": status_counts,
            "by_category": category_stats,
            "total_value": float(total_value),
            "low_stock_count": low_count,
            "out_of_stock_count": out_count,
        }

    # ==================== STOCK ALERTS ====================

    async def get_active_alerts(self) -> List[StockAlert]:
        """Get all active stock alerts."""
        stmt = (
            select(StockAlert)
            .where(StockAlert.status == "active")
            .options(selectinload(StockAlert.item))
            .order_by(StockAlert.severity.desc(), StockAlert.created_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_alerts_by_item(self, item_id: UUID) -> List[StockAlert]:
        """Get all alerts for an item."""
        stmt = (
            select(StockAlert)
            .where(StockAlert.item_id == item_id)
            .order_by(StockAlert.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_critical_alerts(self) -> List[StockAlert]:
        """Get critical stock alerts."""
        stmt = (
            select(StockAlert)
            .where(
                StockAlert.status == "active",
                StockAlert.severity == "critical"
            )
            .options(selectinload(StockAlert.item))
            .order_by(StockAlert.created_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_alert(self, data: Dict[str, Any]) -> StockAlert:
        """Create stock alert."""
        alert = StockAlert(**data)
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by: str,
        note: Optional[str] = None
    ) -> Optional[StockAlert]:
        """Resolve stock alert."""
        stmt = select(StockAlert).where(StockAlert.id == alert_id)
        result = await self.db.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return None

        alert.status = "resolved"
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by
        if note:
            alert.resolution_note = note

        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def check_and_create_alerts(self) -> List[StockAlert]:
        """Check stock and create alerts if needed."""
        items = await self.get_all()
        alerts = []

        for item in items:
            # Check existing active alerts for this item
            existing = await self.get_alerts_by_item(item.id)
            active_existing = [a for a in existing if a.status == "active"]

            # Skip if already has active alert of same type
            if active_existing:
                continue

            if item.current_stock <= 0:
                alert = await self.create_alert({
                    "item_id": item.id,
                    "alert_type": "out_of_stock",
                    "current_stock": item.current_stock,
                    "threshold": Decimal(0),
                    "severity": "critical",
                    "message": f"Item {item.name} is out of stock"
                })
                alerts.append(alert)
            elif item.current_stock <= item.min_stock_threshold:
                severity = "critical" if item.current_stock <= item.min_stock_threshold / 2 else "warning"
                alert = await self.create_alert({
                    "item_id": item.id,
                    "alert_type": "low_stock",
                    "current_stock": item.current_stock,
                    "threshold": item.min_stock_threshold,
                    "severity": severity,
                    "message": f"Item {item.name} is below minimum stock threshold"
                })
                alerts.append(alert)

        return alerts

    # ==================== STOCK OPNAME ====================

    async def get_opnames(self, item_id: UUID) -> List[StockOpname]:
        """Get all opnames for an item."""
        stmt = (
            select(StockOpname)
            .where(StockOpname.item_id == item_id)
            .order_by(StockOpname.performed_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_opname(self, opname_id: UUID) -> Optional[StockOpname]:
        """Get opname by ID."""
        stmt = select(StockOpname).where(StockOpname.id == opname_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_opname(self, data: Dict[str, Any]) -> StockOpname:
        """Create stock opname."""
        item = await self.get(data["item_id"])
        if not item:
            raise NotFoundError(f"Item {data['item_id']} not found")

        system_stock = item.current_stock
        physical_stock = data["physical_stock"]
        difference = physical_stock - system_stock

        opname = StockOpname(
            system_stock=system_stock,
            physical_stock=physical_stock,
            difference=difference,
            **data
        )
        self.db.add(opname)

        await self.db.flush()
        await self.db.refresh(opname)
        return opname

    async def approve_opname(self, opname_id: UUID, approved_by: str) -> Optional[StockOpname]:
        """Approve stock opname and adjust stock."""
        opname = await self.get_opname(opname_id)
        if not opname:
            return None

        opname.approved_by = approved_by
        opname.approved_at = datetime.now()

        if opname.difference != 0:
            item = await self.get(opname.item_id)
            if item:
                item.current_stock = opname.physical_stock
                item.available_stock = item.current_stock - item.reserved_stock

                movement = InventoryStockMovement(
                    item_id=opname.item_id,
                    type=StockMovementType.ADJUSTMENT,
                    quantity=opname.difference,
                    previous_stock=opname.system_stock,
                    new_stock=opname.physical_stock,
                    reference_type="opname",
                    reference_id=opname.id,
                    note=f"Stock adjustment from opname: {opname.adjustment_reason}",
                    performed_by=approved_by
                )
                self.db.add(movement)

        await self.db.flush()
        await self.db.refresh(opname)
        return opname


class InventoryMaterialUsageRepository(BaseRepository[InventoryMaterialUsage]):
    """Repository untuk Inventory Material Usage."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InventoryMaterialUsage)

    async def get_by_project(self, project_id: UUID) -> List[InventoryMaterialUsage]:
        """Get material usage by project."""
        stmt = (
            select(InventoryMaterialUsage)
            .where(InventoryMaterialUsage.project_id == project_id)
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(desc(InventoryMaterialUsage.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_job(self, job_id: UUID) -> List[InventoryMaterialUsage]:
        """Get material usage by workshop job."""
        stmt = (
            select(InventoryMaterialUsage)
            .where(InventoryMaterialUsage.job_id == job_id)
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(desc(InventoryMaterialUsage.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[InventoryMaterialUsage]:
        """Get material usage within date range."""
        stmt = (
            select(InventoryMaterialUsage)
            .where(
                InventoryMaterialUsage.used_at >= start_date,
                InventoryMaterialUsage.used_at <= end_date
            )
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(desc(InventoryMaterialUsage.used_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_material_summary(self, project_id: UUID) -> dict:
        """Get material usage summary for a project."""
        stmt = select(
            InventoryMaterialUsage.item_id,
            func.sum(InventoryMaterialUsage.quantity).label('total_quantity'),
            func.sum(InventoryMaterialUsage.total_cost).label('total_cost')
        ).where(
            InventoryMaterialUsage.project_id == project_id
        ).group_by(InventoryMaterialUsage.item_id)

        result = await self.db.execute(stmt)
        rows = result.all()

        item_summary = []
        for row in rows:
            item = await self.db.get(InventoryItem, row.item_id)
            item_summary.append({
                "item_id": row.item_id,
                "item_name": item.name if item else "Unknown",
                "unit": item.unit if item else "-",
                "total_quantity": row.total_quantity,
                "total_cost": row.total_cost,
            })

        return {
            "total_items": len(rows),
            "total_cost": sum(row.total_cost or 0 for row in rows),
            "items": item_summary
        }

    async def create_usage(
        self,
        item_id: UUID,
        quantity: Decimal,
        project_id: Optional[UUID] = None,
        job_id: Optional[UUID] = None,
        note: Optional[str] = None,
        is_waste: bool = False,
        confirmed_by: Optional[str] = None
    ) -> InventoryMaterialUsage:
        """Create a material usage record and update inventory stock."""
        if not project_id and not job_id:
            raise ValueError("Either project_id or job_id must be provided")

        item = await self.db.get(InventoryItem, item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        usage = InventoryMaterialUsage(
            item_id=item_id,
            quantity=quantity,
            unit_cost=item.cost_price,
            total_cost=quantity * item.cost_price,
            project_id=project_id,
            job_id=job_id,
            note=note,
            is_waste=is_waste,
            confirmed_by=confirmed_by,
            used_at=datetime.now()
        )

        self.db.add(usage)

        # Update inventory stock via repository
        inventory_repo = InventoryRepository(self.db)
        await inventory_repo.update_stock(
            item_id=item_id,
            quantity=quantity,
            movement_type=StockMovementType.USAGE,
            reference_type="material_usage",
            reference_id=usage.id,
            note=f"Material used for {'project' if project_id else 'job'}",
            performed_by=confirmed_by
        )

        await self.db.flush()
        await self.db.refresh(usage)
        return usage


class InventoryStockMovementRepository(BaseRepository[InventoryStockMovement]):
    """Repository untuk Inventory Stock Movement."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InventoryStockMovement)

    async def get_by_item(self, item_id: UUID, limit: int = 50) -> List[InventoryStockMovement]:
        """Get stock movements by item."""
        stmt = (
            select(InventoryStockMovement)
            .where(InventoryStockMovement.item_id == item_id)
            .options(selectinload(InventoryStockMovement.item))
            .order_by(desc(InventoryStockMovement.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent_movements(self, limit: int = 10) -> List[InventoryStockMovement]:
        """Get recent stock movements."""
        stmt = (
            select(InventoryStockMovement)
            .options(selectinload(InventoryStockMovement.item))
            .order_by(desc(InventoryStockMovement.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_summary_by_type(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> dict:
        """Get stock movement summary by type."""
        stmt = select(
            InventoryStockMovement.type,
            func.sum(InventoryStockMovement.quantity).label('total_quantity')
        ).where(
            InventoryStockMovement.created_at >= period_start,
            InventoryStockMovement.created_at <= period_end
        ).group_by(InventoryStockMovement.type)

        result = await self.db.execute(stmt)
        rows = result.all()
        return {row.type: row.total_quantity for row in rows}

    async def get_movement_report(
        self,
        start_date: datetime,
        end_date: datetime,
        movement_type: Optional[str] = None
    ) -> List[InventoryStockMovement]:
        """Get detailed movement report."""
        filters = [
            InventoryStockMovement.created_at >= start_date,
            InventoryStockMovement.created_at <= end_date
        ]
        if movement_type:
            filters.append(InventoryStockMovement.type == movement_type)

        stmt = (
            select(InventoryStockMovement)
            .where(and_(*filters))
            .options(selectinload(InventoryStockMovement.item))
            .order_by(desc(InventoryStockMovement.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


class ProjectWorkshopJobRepository(BaseRepository[ProjectWorkshopTask]):
    """Repository untuk Project Workshop Task."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=ProjectWorkshopTask)

    async def get_by_project(self, project_id: UUID) -> Optional[ProjectWorkshopTask]:
        """Get workshop task by project."""
        stmt = (
            select(ProjectWorkshopTask)
            .where(ProjectWorkshopTask.project_id == project_id)
            .options(
                selectinload(ProjectWorkshopTask.material_usages)
                .selectinload(InventoryMaterialUsage.item)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_materials(self, job_id: UUID) -> Optional[ProjectWorkshopTask]:
        """Get workshop job with all material usages."""
        stmt = (
            select(ProjectWorkshopTask)
            .where(ProjectWorkshopTask.id == job_id)
            .options(
                selectinload(ProjectWorkshopTask.material_usages)
                .selectinload(InventoryMaterialUsage.item),
                selectinload(ProjectWorkshopTask.project),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def calculate_actual_cost(self, job_id: UUID) -> Decimal:
        """Calculate actual cost for a workshop job."""
        job = await self.get(job_id)
        if not job:
            return Decimal(0)

        stmt = select(
            func.sum(InventoryMaterialUsage.total_cost)
        ).where(InventoryMaterialUsage.job_id == job_id)
        result = await self.db.execute(stmt)
        material_cost = result.scalar() or Decimal(0)

        total_cost = job.actual_cost + material_cost
        job.actual_cost = total_cost
        await self.db.flush()
        return total_cost

    async def update_status(
        self,
        job_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[ProjectWorkshopTask]:
        """Update workshop job status."""
        job = await self.get(job_id)
        if not job:
            return None

        old_status = job.status
        job.status = status

        if status == "completed":
            job.completed_at = datetime.now()
        elif status == "in_progress":
            job.start_date = datetime.now()

        if note:
            job.notes = note

        await self.db.flush()
        await self.db.refresh(job)
        return job


class SupplierRepository(BaseRepository[Supplier]):
    """Repository untuk Supplier."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=Supplier)

    async def list_active(self) -> List[Supplier]:
        """List all active suppliers."""
        stmt = select(Supplier).where(Supplier.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_with_count(self) -> List[dict]:
        """List suppliers with item counts."""
        stmt = (
            select(
                Supplier.id,
                Supplier.name,
                Supplier.phone,
                Supplier.email,
                Supplier.is_active,
                func.count(InventoryItem.id).label('item_count')
            )
            .outerjoin(InventoryItem, InventoryItem.supplier_id == Supplier.id)
            .group_by(Supplier.id)
            .order_by(Supplier.name)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": row.id,
                "name": row.name,
                "phone": row.phone,
                "email": row.email,
                "is_active": row.is_active,
                "item_count": row.item_count
            }
            for row in rows
        ]


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    """Repository untuk Purchase Order."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=PurchaseOrder)

    async def get_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """Get purchase order by PO number."""
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.po_number == po_number)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, po_id: UUID) -> Optional[PurchaseOrder]:
        """Get purchase order with all details."""
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items)
                .selectinload(PurchaseOrderItem.item)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_supplier(
        self,
        supplier_id: UUID,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[PurchaseOrder]:
        """List purchase orders by supplier."""
        filters = [PurchaseOrder.supplier_id == supplier_id]
        if status:
            filters.append(PurchaseOrder.status == status)

        stmt = (
            select(PurchaseOrder)
            .where(and_(*filters))
            .order_by(desc(PurchaseOrder.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_pending_orders(self) -> List[PurchaseOrder]:
        """Get pending purchase orders."""
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.status.in_(["draft", "ordered", "received_partial"]))
            .options(selectinload(PurchaseOrder.supplier))
            .order_by(PurchaseOrder.expected_delivery)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        po_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[PurchaseOrder]:
        """Update purchase order status."""
        po = await self.get(po_id)
        if not po:
            return None

        po.status = status
        if note:
            po.notes = note

        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def receive_order(
        self,
        po_id: UUID,
        received_items: Dict[UUID, Decimal],
        received_by: str
    ) -> Optional[PurchaseOrder]:
        """Receive items in a purchase order and update inventory."""
        po = await self.get_with_details(po_id)
        if not po:
            return None

        inventory_repo = InventoryRepository(self.db)

        for item in po.items:
            if item.id in received_items:
                qty = received_items[item.id]
                if qty > 0:
                    item.received_quantity += qty

                    await inventory_repo.update_stock(
                        item_id=item.item_id,
                        quantity=qty,
                        movement_type=StockMovementType.PURCHASE,
                        reference_type="purchase_order",
                        reference_id=po.id,
                        note=f"Received from PO {po.po_number}",
                        performed_by=received_by
                    )

        all_received = all(
            item.received_quantity >= item.quantity
            for item in po.items
        )

        if all_received:
            po.status = "completed"
            po.actual_delivery = datetime.now()
        else:
            po.status = "received_partial"

        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def generate_po_number(self) -> str:
        """Generate a unique PO number."""
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")

        stmt = select(func.max(PurchaseOrder.po_number)).where(
            PurchaseOrder.po_number.ilike(f"PO-{year}{month}-%")
        )
        result = await self.db.execute(stmt)
        last_number = result.scalar()

        if last_number:
            parts = last_number.split("-")
            if len(parts) == 3:
                try:
                    seq = int(parts[2])
                    seq += 1
                except ValueError:
                    seq = 1
            else:
                seq = 1
        else:
            seq = 1

        return f"PO-{year}{month}-{str(seq).zfill(5)}"
