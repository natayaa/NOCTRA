# modules/inventory/repository.py
"""
Inventory Repository - REFACTORED

✅ Soft delete support (is_deleted filter di semua query)
✅ Clear separation: InventoryRepository, MaterialUsageRepository, StockMovementRepository
✅ WorkshopJobRepository, SupplierRepository, PurchaseOrderRepository
✅ Lazy loading with selectinload
✅ Stock calculations with Decimal
"""

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
    """Repository untuk Inventory Item - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InventoryItem)

    # ============================================================
    # READ OPERATIONS
    # ============================================================

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[InventoryItem]:
        """Get item by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str, include_deleted: bool = False) -> Optional[InventoryItem]:
        """Get item by SKU."""
        stmt = select(InventoryItem).where(InventoryItem.sku == sku)
        if not include_deleted:
            stmt = stmt.where(InventoryItem.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_barcode(self, barcode: str, include_deleted: bool = False) -> Optional[InventoryItem]:
        """Get item by barcode."""
        stmt = select(InventoryItem).where(InventoryItem.barcode == barcode)
        if not include_deleted:
            stmt = stmt.where(InventoryItem.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, item_id: UUID) -> Optional[InventoryItem]:
        """Get item with all related data."""
        stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.id == item_id,
                InventoryItem.is_deleted == False
            )
            .options(
                selectinload(InventoryItem.supplier),
                selectinload(InventoryItem.price_list_item),
                selectinload(InventoryItem.material_usages),
                selectinload(InventoryItem.stock_movements),
                selectinload(InventoryItem.alerts),
                selectinload(InventoryItem.opnames),
                selectinload(InventoryItem.valuations),
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
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[InventoryItem], int]:
        """List items with filters."""
        stmt = select(InventoryItem)
        count_stmt = select(func.count()).select_from(InventoryItem)

        filters = []
        if not include_deleted:
            filters.append(InventoryItem.is_deleted == False)
        if category:
            filters.append(InventoryItem.category == category)
        if status:
            filters.append(InventoryItem.status == status)
        if low_stock_only:
            filters.append(InventoryItem.current_stock <= InventoryItem.min_stock_threshold)
        if search:
            filters.append(
                or_(
                    InventoryItem.name.ilike(f"%{search}%"),
                    InventoryItem.sku.ilike(f"%{search}%"),
                    InventoryItem.barcode.ilike(f"%{search}%"),
                    InventoryItem.description.ilike(f"%{search}%"),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.options(
            selectinload(InventoryItem.supplier),
            selectinload(InventoryItem.price_list_item)
        )
        stmt = stmt.order_by(InventoryItem.name).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return items, total

    async def get_by_category(self, category: str, include_deleted: bool = False) -> List[InventoryItem]:
        """Get items by category."""
        stmt = select(InventoryItem).where(InventoryItem.category == category)
        if not include_deleted:
            stmt = stmt.where(InventoryItem.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_low_stock_items(self, include_deleted: bool = False) -> List[InventoryItem]:
        """Get all low stock items."""
        stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.current_stock <= InventoryItem.min_stock_threshold,
                InventoryItem.is_deleted == False
            )
            .order_by(InventoryItem.current_stock)
            .options(
                selectinload(InventoryItem.supplier),
                selectinload(InventoryItem.price_list_item)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_out_of_stock_items(self, include_deleted: bool = False) -> List[InventoryItem]:
        """Get all out of stock items."""
        stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.current_stock <= 0,
                InventoryItem.is_deleted == False
            )
            .order_by(InventoryItem.name)
            .options(
                selectinload(InventoryItem.supplier),
                selectinload(InventoryItem.price_list_item)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        stmt = select(InventoryItem.category).distinct().where(
            InventoryItem.is_deleted == False
        ).order_by(InventoryItem.category)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_items_by_ids(self, ids: List[UUID]) -> List[InventoryItem]:
        """Get multiple items by IDs."""
        if not ids:
            return []
        stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.id.in_(ids),
                InventoryItem.is_deleted == False
            )
            .options(
                selectinload(InventoryItem.supplier),
                selectinload(InventoryItem.price_list_item)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # STOCK UPDATE OPERATIONS
    # ============================================================

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
        """Update item stock with movement tracking - TANPA flush."""
        item = await self.get(item_id)
        if not item or item.is_deleted:
            return None

        previous_stock = item.current_stock

        if movement_type in [StockMovementType.PURCHASE, StockMovementType.RETURN, StockMovementType.RECEIVED]:
            item.current_stock += quantity
        elif movement_type in [StockMovementType.SALE, StockMovementType.USAGE, StockMovementType.WASTE, StockMovementType.SHIPPED]:
            if item.current_stock < quantity:
                raise ValueError(
                    f"Insufficient stock. Current: {item.current_stock}, Required: {quantity}"
                )
            item.current_stock -= quantity
        elif movement_type == StockMovementType.ADJUSTMENT:
            if quantity < 0 and abs(quantity) > item.current_stock:
                raise ValueError(
                    f"Insufficient stock for adjustment. Current: {item.current_stock}, Adjustment: {quantity}"
                )
            item.current_stock += quantity
        else:
            raise ValueError(f"Invalid movement type: {movement_type}")

        # Update status if out of stock
        if item.current_stock <= 0:
            item.status = InventoryStatus.OUT_OF_STOCK
        elif item.current_stock <= item.min_stock_threshold:
            item.status = InventoryStatus.LOW_STOCK
        elif item.status in [InventoryStatus.OUT_OF_STOCK, InventoryStatus.LOW_STOCK]:
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

        return item

    async def reserve_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID
    ) -> Optional[InventoryItem]:
        """Reserve stock for a project or job - TANPA flush."""
        item = await self.get(item_id)
        if not item or item.is_deleted:
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

        return item

    async def release_reserved_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID
    ) -> Optional[InventoryItem]:
        """Release reserved stock - TANPA flush."""
        item = await self.get(item_id)
        if not item or item.is_deleted:
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

        return item

    # ============================================================
    # DELETE OPERATIONS
    # ============================================================

    async def delete(self, pk: UUID) -> bool:
        """Soft delete inventory item - TANPA flush."""
        item = await self.get(pk)
        if not item:
            return False

        # Check if item is used in any active purchase order
        stmt = select(func.count()).select_from(PurchaseOrderItem).where(
            PurchaseOrderItem.item_id == pk,
            PurchaseOrderItem.is_deleted == False
        )
        count = await self.db.scalar(stmt) or 0
        if count > 0:
            raise ValueError(f"Cannot delete item with {count} active purchase order items")

        item.is_deleted = True
        item.deleted_at = datetime.now()
        item.status = InventoryStatus.INACTIVE
        return True

    async def hard_delete(self, pk: UUID) -> bool:
        """Hard delete inventory item - TANPA flush."""
        item = await self.get(pk, include_deleted=True)
        if not item:
            return False

        await self.db.delete(item)
        return True

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(self) -> dict:
        """Get inventory statistics."""
        total_stmt = select(func.count()).select_from(InventoryItem).where(
            InventoryItem.is_deleted == False
        )
        total = await self.db.scalar(total_stmt) or 0

        status_stmt = (
            select(InventoryItem.status, func.count().label('count'))
            .where(InventoryItem.is_deleted == False)
            .group_by(InventoryItem.status)
        )
        result_status = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in result_status}

        category_stmt = (
            select(
                InventoryItem.category,
                func.count().label('count'),
                func.sum(InventoryItem.current_stock).label('total_stock')
            )
            .where(InventoryItem.is_deleted == False)
            .group_by(InventoryItem.category)
        )
        result_category = await self.db.execute(category_stmt)
        category_stats = {
            row.category: {"count": row.count, "total_stock": row.total_stock}
            for row in result_category
        }

        value_stmt = select(
            func.sum(InventoryItem.current_stock * InventoryItem.cost_price)
        ).where(InventoryItem.is_deleted == False)
        total_value = await self.db.scalar(value_stmt) or Decimal(0)

        low_count_stmt = select(func.count()).select_from(InventoryItem).where(
            InventoryItem.current_stock <= InventoryItem.min_stock_threshold,
            InventoryItem.is_deleted == False
        )
        low_count = await self.db.scalar(low_count_stmt) or 0

        out_count_stmt = select(func.count()).select_from(InventoryItem).where(
            InventoryItem.current_stock <= 0,
            InventoryItem.is_deleted == False
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

    # ============================================================
    # STOCK ALERTS
    # ============================================================

    async def get_active_alerts(self) -> List[StockAlert]:
        """Get all active stock alerts."""
        stmt = (
            select(StockAlert)
            .where(
                StockAlert.status == "active",
                StockAlert.is_deleted == False
            )
            .options(selectinload(StockAlert.item))
            .order_by(StockAlert.severity.desc(), StockAlert.created_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_alerts_by_item(self, item_id: UUID) -> List[StockAlert]:
        """Get all alerts for an item."""
        stmt = (
            select(StockAlert)
            .where(
                StockAlert.item_id == item_id,
                StockAlert.is_deleted == False
            )
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
                StockAlert.severity == "critical",
                StockAlert.is_deleted == False
            )
            .options(selectinload(StockAlert.item))
            .order_by(StockAlert.created_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_alert(self, data: Dict[str, Any]) -> StockAlert:
        """Create stock alert - TANPA flush."""
        alert = StockAlert(**data)
        self.db.add(alert)
        return alert

    async def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by: str,
        note: Optional[str] = None
    ) -> Optional[StockAlert]:
        """Resolve stock alert - TANPA flush."""
        stmt = select(StockAlert).where(
            StockAlert.id == alert_id,
            StockAlert.is_deleted == False
        )
        result = await self.db.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return None

        alert.status = "resolved"
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by
        if note:
            alert.resolution_note = note

        return alert

    async def check_and_create_alerts(self) -> List[StockAlert]:
        """Check stock and create alerts if needed - TANPA flush."""
        items = await self.get_all()
        alerts = []

        for item in items:
            if item.is_deleted:
                continue

            existing = await self.get_alerts_by_item(item.id)
            active_existing = [a for a in existing if a.status == "active"]

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

    # ============================================================
    # STOCK OPNAME
    # ============================================================

    async def get_opnames(self, item_id: UUID) -> List[StockOpname]:
        """Get all opnames for an item."""
        stmt = (
            select(StockOpname)
            .where(
                StockOpname.item_id == item_id,
                StockOpname.is_deleted == False
            )
            .order_by(StockOpname.performed_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_opname(self, opname_id: UUID) -> Optional[StockOpname]:
        """Get opname by ID."""
        stmt = select(StockOpname).where(
            StockOpname.id == opname_id,
            StockOpname.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_opname(self, data: Dict[str, Any]) -> StockOpname:
        """Create stock opname - TANPA flush."""
        item = await self.get(data["item_id"])
        if not item or item.is_deleted:
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
        return opname

    async def approve_opname(
        self,
        opname_id: UUID,
        approved_by: str
    ) -> Optional[StockOpname]:
        """Approve stock opname and adjust stock - TANPA flush."""
        opname = await self.get_opname(opname_id)
        if not opname:
            return None

        opname.approved_by = approved_by
        opname.approved_at = datetime.now()

        if opname.difference != 0:
            item = await self.get(opname.item_id)
            if item and not item.is_deleted:
                item.current_stock = opname.physical_stock
                item.available_stock = item.current_stock - item.reserved_stock

                # Update status
                if item.current_stock <= 0:
                    item.status = InventoryStatus.OUT_OF_STOCK
                elif item.current_stock <= item.min_stock_threshold:
                    item.status = InventoryStatus.LOW_STOCK
                else:
                    item.status = InventoryStatus.ACTIVE

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

        return opname


class InventoryMaterialUsageRepository(BaseRepository[InventoryMaterialUsage]):
    """Repository untuk Inventory Material Usage - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InventoryMaterialUsage)

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[InventoryMaterialUsage]:
        """Get material usage by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_project(
        self,
        project_id: UUID,
        include_deleted: bool = False
    ) -> List[InventoryMaterialUsage]:
        """Get material usage by project."""
        stmt = (
            select(InventoryMaterialUsage)
            .where(InventoryMaterialUsage.project_id == project_id)
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(desc(InventoryMaterialUsage.created_at))
        )
        if not include_deleted:
            stmt = stmt.where(InventoryMaterialUsage.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_job(
        self,
        job_id: UUID,
        include_deleted: bool = False
    ) -> List[InventoryMaterialUsage]:
        """Get material usage by workshop job."""
        stmt = (
            select(InventoryMaterialUsage)
            .where(InventoryMaterialUsage.job_id == job_id)
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(desc(InventoryMaterialUsage.created_at))
        )
        if not include_deleted:
            stmt = stmt.where(InventoryMaterialUsage.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        include_deleted: bool = False
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
        if not include_deleted:
            stmt = stmt.where(InventoryMaterialUsage.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_material_summary(self, project_id: UUID) -> dict:
        """Get material usage summary for a project."""
        stmt = select(
            InventoryMaterialUsage.item_id,
            func.sum(InventoryMaterialUsage.quantity).label('total_quantity'),
            func.sum(InventoryMaterialUsage.total_cost).label('total_cost')
        ).where(
            InventoryMaterialUsage.project_id == project_id,
            InventoryMaterialUsage.is_deleted == False
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
        """Create a material usage record - TANPA flush."""
        if not project_id and not job_id:
            raise ValueError("Either project_id or job_id must be provided")

        item = await self.db.get(InventoryItem, item_id)
        if not item or item.is_deleted:
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
        return usage

    async def delete(self, pk: UUID) -> bool:
        """Soft delete material usage - TANPA flush."""
        usage = await self.get(pk)
        if not usage:
            return False

        usage.is_deleted = True
        usage.deleted_at = datetime.now()
        return True


class InventoryStockMovementRepository(BaseRepository[InventoryStockMovement]):
    """Repository untuk Inventory Stock Movement - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InventoryStockMovement)

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[InventoryStockMovement]:
        """Get stock movement by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_item(
        self,
        item_id: UUID,
        limit: int = 50,
        include_deleted: bool = False
    ) -> List[InventoryStockMovement]:
        """Get stock movements by item."""
        stmt = (
            select(InventoryStockMovement)
            .where(InventoryStockMovement.item_id == item_id)
            .options(selectinload(InventoryStockMovement.item))
            .order_by(desc(InventoryStockMovement.created_at))
            .limit(limit)
        )
        if not include_deleted:
            stmt = stmt.where(InventoryStockMovement.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent_movements(
        self,
        limit: int = 10,
        include_deleted: bool = False
    ) -> List[InventoryStockMovement]:
        """Get recent stock movements."""
        stmt = (
            select(InventoryStockMovement)
            .options(selectinload(InventoryStockMovement.item))
            .order_by(desc(InventoryStockMovement.created_at))
            .limit(limit)
        )
        if not include_deleted:
            stmt = stmt.where(InventoryStockMovement.is_deleted == False)
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
            InventoryStockMovement.created_at <= period_end,
            InventoryStockMovement.is_deleted == False
        ).group_by(InventoryStockMovement.type)

        result = await self.db.execute(stmt)
        rows = result.all()
        return {row.type: row.total_quantity for row in rows}

    async def get_movement_report(
        self,
        start_date: datetime,
        end_date: datetime,
        movement_type: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[InventoryStockMovement]:
        """Get detailed movement report."""
        filters = [
            InventoryStockMovement.created_at >= start_date,
            InventoryStockMovement.created_at <= end_date,
            InventoryStockMovement.is_deleted == False
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
    """Repository untuk Project Workshop Task - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=ProjectWorkshopTask)

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[ProjectWorkshopTask]:
        """Get workshop job by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_project(self, project_id: UUID) -> Optional[ProjectWorkshopTask]:
        """Get workshop task by project."""
        stmt = (
            select(ProjectWorkshopTask)
            .where(
                ProjectWorkshopTask.project_id == project_id,
                ProjectWorkshopTask.is_deleted == False
            )
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
            .where(
                ProjectWorkshopTask.id == job_id,
                ProjectWorkshopTask.is_deleted == False
            )
            .options(
                selectinload(ProjectWorkshopTask.material_usages)
                .selectinload(InventoryMaterialUsage.item),
                selectinload(ProjectWorkshopTask.project),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def calculate_actual_cost(self, job_id: UUID) -> Decimal:
        """Calculate actual cost for a workshop job - TANPA flush."""
        job = await self.get(job_id)
        if not job or job.is_deleted:
            return Decimal(0)

        stmt = select(
            func.sum(InventoryMaterialUsage.total_cost)
        ).where(
            InventoryMaterialUsage.job_id == job_id,
            InventoryMaterialUsage.is_deleted == False
        )
        result = await self.db.execute(stmt)
        material_cost = result.scalar() or Decimal(0)

        total_cost = job.actual_cost + material_cost
        job.actual_cost = total_cost

        return total_cost

    async def update_status(
        self,
        job_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[ProjectWorkshopTask]:
        """Update workshop job status - TANPA flush."""
        job = await self.get(job_id)
        if not job or job.is_deleted:
            return None

        job.status = status

        if status == "completed":
            job.completed_at = datetime.now()
        elif status == "in_progress":
            job.start_date = datetime.now()

        if note:
            job.notes = note

        return job

    async def delete(self, pk: UUID) -> bool:
        """Soft delete workshop job - TANPA flush."""
        job = await self.get(pk)
        if not job:
            return False

        job.is_deleted = True
        job.deleted_at = datetime.now()
        return True


class SupplierRepository(BaseRepository[Supplier]):
    """Repository untuk Supplier - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=Supplier)

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[Supplier]:
        """Get supplier by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> List[Supplier]:
        """List all active suppliers."""
        stmt = select(Supplier).where(
            Supplier.is_active == True,
            Supplier.is_deleted == False
        )
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
            .where(Supplier.is_deleted == False)
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

    async def delete(self, pk: UUID) -> bool:
        """Soft delete supplier - TANPA flush."""
        supplier = await self.get(pk)
        if not supplier:
            return False

        # Check if supplier has active items
        stmt = select(func.count()).select_from(InventoryItem).where(
            InventoryItem.supplier_id == pk,
            InventoryItem.is_deleted == False
        )
        count = await self.db.scalar(stmt) or 0
        if count > 0:
            raise ValueError(f"Cannot delete supplier with {count} active items")

        supplier.is_deleted = True
        supplier.deleted_at = datetime.now()
        supplier.is_active = False
        return True


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    """Repository untuk Purchase Order - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=PurchaseOrder)

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[PurchaseOrder]:
        """Get purchase order by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """Get purchase order by PO number."""
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.po_number == po_number,
            PurchaseOrder.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, po_id: UUID) -> Optional[PurchaseOrder]:
        """Get purchase order with all details."""
        stmt = (
            select(PurchaseOrder)
            .where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.is_deleted == False
            )
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
        filters = [
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.is_deleted == False
        ]
        if status:
            filters.append(PurchaseOrder.status == status)

        stmt = (
            select(PurchaseOrder)
            .where(and_(*filters))
            .order_by(desc(PurchaseOrder.created_at))
            .limit(limit)
            .options(selectinload(PurchaseOrder.supplier))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_pending_orders(self) -> List[PurchaseOrder]:
        """Get pending purchase orders."""
        stmt = (
            select(PurchaseOrder)
            .where(
                PurchaseOrder.status.in_(["draft", "ordered", "received_partial"]),
                PurchaseOrder.is_deleted == False
            )
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
        """Update purchase order status - TANPA flush."""
        po = await self.get(po_id)
        if not po or po.is_deleted:
            return None

        po.status = status
        if note:
            po.notes = note

        return po

    async def receive_order(
        self,
        po_id: UUID,
        received_items: Dict[UUID, Decimal],
        received_by: str
    ) -> Optional[PurchaseOrder]:
        """Receive items in a purchase order - TANPA flush."""
        po = await self.get_with_details(po_id)
        if not po or po.is_deleted:
            return None

        inventory_repo = InventoryRepository(self.db)

        for item in po.items:
            if item.id in received_items:
                qty = received_items[item.id]
                if qty > 0:
                    item.received_quantity += qty

                    # Update inventory stock
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

        return po

    async def generate_po_number(self) -> str:
        """Generate a unique PO number."""
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")

        stmt = select(func.max(PurchaseOrder.po_number)).where(
            PurchaseOrder.po_number.ilike(f"PO-{year}{month}-%"),
            PurchaseOrder.is_deleted == False
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

    async def delete(self, pk: UUID) -> bool:
        """Soft delete purchase order - TANPA flush."""
        po = await self.get(pk)
        if not po:
            return False

        # Check if PO has been received
        if po.status in ["completed", "received_partial"]:
            raise ValueError("Cannot delete purchase order that has been received")

        po.is_deleted = True
        po.deleted_at = datetime.now()
        return True