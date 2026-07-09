# modules/inventory/service.py
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.exceptions import NotFoundError, ValidationError, BusinessError
from core.constants import InventoryStatus, StockMovementType
from .models import (
    InventoryItem,
    InventoryMaterialUsage,
    InventoryStockMovement,
    ProjectWorkshopTask,
    StockAlert,
    StockOpname,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem
)
from modules.inventory.repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,
    ProjectWorkshopJobRepository,
    SupplierRepository,
    PurchaseOrderRepository
)
from modules.inventory.schemas import (
    CreateInventoryItem,
    StockAlertResponse,
    StockOpnameCreate,
    UpdateInventoryItem,
    CreateInventoryMaterialUsage,
    CreateInventoryStockMovement,
    CreatePurchaseOrder,
    CreateSupplier
)

# Import dengan TYPE_CHECKING untuk menghindari circular import
if TYPE_CHECKING:
    from modules.projects.repository import ProjectRepository


class InventoryService:
    """Service untuk Inventory management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.item_repo = InventoryRepository(db)
        self.usage_repo = InventoryMaterialUsageRepository(db)
        self.movement_repo = InventoryStockMovementRepository(db)
        self.workshop_repo = ProjectWorkshopJobRepository(db)
        self.supplier_repo = SupplierRepository(db)
        self.po_repo = PurchaseOrderRepository(db)
        self.project_repo = None  # ProjectRepository(db)

    # =========================================================================
    # Item Management
    # =========================================================================

    async def create_item(self, data: CreateInventoryItem) -> InventoryItem:
        """Create a new inventory item."""
        # Check if SKU already exists
        if data.sku:
            existing = await self.item_repo.get_by_sku(data.sku)
            if existing:
                raise ValidationError(f"SKU '{data.sku}' already exists")

        # Check if barcode already exists
        if data.barcode:
            existing = await self.item_repo.get_by_barcode(data.barcode)
            if existing:
                raise ValidationError(
                    f"Barcode '{data.barcode}' already exists")

        # Prepare data with auto-calculated status
        item_data = data.model_dump()

        # Auto-set status based on stock level
        current_stock = item_data.get('current_stock', 0)
        min_threshold = item_data.get('min_stock_threshold', 0)

        if current_stock <= 0:
            item_data['status'] = "out_of_stock"
        elif current_stock <= min_threshold:
            item_data['status'] = "low_stock"
        else:
            item_data['status'] = "active"

        # Calculate available stock
        reserved_stock = item_data.get('reserved_stock', 0)
        item_data['available_stock'] = current_stock - reserved_stock

        # ✅ Buat instance model dulu, baru kirim ke repository
        item = InventoryItem(**item_data)
        return await self.item_repo.create(item)

    async def get_item(self, item_id: UUID) -> Optional[InventoryItem]:
        """Get inventory item by ID."""
        return await self.item_repo.get(item_id)

    async def get_item_with_details(self, item_id: UUID) -> Optional[InventoryItem]:
        """Get inventory item with all details."""
        return await self.item_repo.get_with_details(item_id)

    async def get_item_by_sku(self, sku: str) -> Optional[InventoryItem]:
        """Get item by SKU."""
        return await self.item_repo.get_by_sku(sku)

    async def get_item_by_barcode(self, barcode: str) -> Optional[InventoryItem]:
        """Get item by barcode."""
        return await self.item_repo.get_by_barcode(barcode)

    async def list_items(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        low_stock_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[InventoryItem], int]:
        """List inventory items with filters."""
        return await self.item_repo.list_with_filters(
            category=category,
            status=status,
            search=search,
            low_stock_only=low_stock_only,
            limit=limit,
            offset=offset
        )

    async def update_item(
        self,
        item_id: UUID,
        data: UpdateInventoryItem
    ) -> Optional[InventoryItem]:
        """Update inventory item."""
        item = await self.item_repo.get(item_id)
        if not item:
            raise NotFoundError(f"Item {item_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Check SKU uniqueness if updating
        if data.sku and data.sku != item.sku:
            existing = await self.item_repo.get_by_sku(data.sku)
            if existing:
                raise ValidationError(f"SKU '{data.sku}' already exists")

        # Check barcode uniqueness if updating
        if data.barcode and data.barcode != item.barcode:
            existing = await self.item_repo.get_by_barcode(data.barcode)
            if existing:
                raise ValidationError(
                    f"Barcode '{data.barcode}' already exists")

        item = await self.item_repo.update(item_id, update_data)
        return item

    async def delete_item(self, item_id: UUID) -> bool:
        """Soft delete inventory item."""
        return await self.item_repo.soft_delete(item_id)

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return await self.item_repo.get_categories()

    # =========================================================================
    # Stock Management
    # =========================================================================

    async def adjust_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        movement_type: str,
        reference_type: str,
        reference_id: Optional[UUID] = None,
        note: Optional[str] = None,
        performed_by: Optional[str] = None
    ) -> InventoryStockMovement:
        """Adjust stock and record movement."""
        item = await self.item_repo.get(item_id)
        if not item:
            raise NotFoundError(f"Item {item_id} not found")

        valid_types = [t.value for t in StockMovementType]
        if movement_type not in valid_types:
            raise ValidationError(f"Invalid movement type: {movement_type}")

        # Update stock
        await self.item_repo.update_stock(
            item_id=item_id,
            quantity=quantity,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
            performed_by=performed_by
        )

        # Get the movement record (last created)
        movements = await self.movement_repo.get_by_item(item_id, limit=1)
        if not movements:
            raise ValidationError("Failed to create stock movement")

        return movements[0]

    async def reserve_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID,
        performed_by: Optional[str] = None
    ) -> InventoryItem:
        """Reserve stock for a project or job."""
        return await self.item_repo.reserve_stock(
            item_id=item_id,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id
        )

    async def release_reserved_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID
    ) -> InventoryItem:
        """Release reserved stock."""
        return await self.item_repo.release_reserved_stock(
            item_id=item_id,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id
        )

    async def consume_material(
        self,
        project_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        note: Optional[str] = None,
        job_id: Optional[UUID] = None,
        is_waste: bool = False,
        confirmed_by: Optional[str] = None
    ) -> InventoryMaterialUsage:
        """Consume material for a project."""
        item = await self.item_repo.get(item_id)
        if not item:
            raise NotFoundError(f"Item {item_id} not found")

        # Check stock
        if item.current_stock < quantity:
            raise ValidationError(
                f"Insufficient stock. Available: {item.current_stock} {item.unit}, "
                f"Required: {quantity} {item.unit}"
            )

        # Get or create workshop job
        if not job_id:
            job = await self._get_or_create_workshop_job(project_id)
            job_id = job.id

        # Create material usage
        usage = await self.usage_repo.create_usage(
            item_id=item_id,
            quantity=quantity,
            project_id=project_id,
            job_id=job_id,
            note=note,
            is_waste=is_waste,
            confirmed_by=confirmed_by
        )

        # Update project actual cost (if project_repo available)
        if self.project_repo:
            project = await self.project_repo.get(project_id)
            if project:
                project.actual_cost = (
                    project.actual_cost or 0) + usage.total_cost
                await self.db.flush()

            # Add activity to project
            await self.project_repo.add_activity(
                project_id,
                f"Material consumed: {item.name} x {quantity} {item.unit}",
                "material_consumption",
                performed_by=confirmed_by or "system"
            )

        return usage

    async def _get_or_create_workshop_job(
        self,
        project_id: UUID
    ) -> ProjectWorkshopTask:
        """Get or create workshop job for a project."""
        job = await self.workshop_repo.get_by_project(project_id)
        if not job:
            project_name = f"Project {project_id}"
            estimated_cost = Decimal(0)

            if self.project_repo:
                project = await self.project_repo.get(project_id)
                if project:
                    project_name = project.name or project_name
                    estimated_cost = project.estimated_cost or Decimal(0)

            job = ProjectWorkshopTask(
                project_id=project_id,
                unit_name=project_name,
                status="pending",
                estimated_cost=estimated_cost
            )
            self.db.add(job)
            await self.db.flush()
            await self.db.refresh(job)
        return job

    async def get_project_material_usage(
        self,
        project_id: UUID
    ) -> dict:
        """Get material usage summary for a project."""
        return await self.usage_repo.get_project_material_summary(project_id)

    # =========================================================================
    # Stock Movements
    # =========================================================================

    async def get_item_movements(
        self,
        item_id: UUID,
        limit: int = 50
    ) -> List[InventoryStockMovement]:
        """Get stock movements for an item."""
        return await self.movement_repo.get_by_item(item_id, limit)

    async def get_recent_movements(self, limit: int = 10) -> List[InventoryStockMovement]:
        """Get recent stock movements."""
        return await self.movement_repo.get_recent_movements(limit)

    async def get_movement_report(
        self,
        start_date: datetime,
        end_date: datetime,
        movement_type: Optional[str] = None
    ) -> List[InventoryStockMovement]:
        """Get detailed movement report."""
        return await self.movement_repo.get_movement_report(
            start_date, end_date, movement_type
        )

    # =========================================================================
    # Workshop Jobs
    # =========================================================================

    async def get_workshop_job(self, project_id: UUID) -> Optional[ProjectWorkshopTask]:
        """Get workshop job for a project."""
        return await self.workshop_repo.get_by_project(project_id)

    async def update_workshop_job_status(
        self,
        job_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[ProjectWorkshopTask]:
        """Update workshop job status."""
        job = await self.workshop_repo.update_status(job_id, status, note)
        if job and job.project_id and self.project_repo:
            await self.project_repo.add_activity(
                job.project_id,
                f"Workshop job status updated: {status}",
                "workshop_update",
                performed_by="system"
            )
        return job

    async def calculate_workshop_cost(self, job_id: UUID) -> Decimal:
        """Calculate total cost for a workshop job."""
        return await self.workshop_repo.calculate_actual_cost(job_id)

    # =========================================================================
    # Supplier Management
    # =========================================================================

    async def create_supplier(self, data: CreateSupplier) -> Supplier:
        """Create a new supplier."""
        return await self.supplier_repo.create(data)

    async def get_supplier(self, supplier_id: UUID) -> Optional[Supplier]:
        """Get supplier by ID."""
        return await self.supplier_repo.get(supplier_id)

    async def list_suppliers(self, active_only: bool = True) -> List[Supplier]:
        """List all suppliers."""
        if active_only:
            return await self.supplier_repo.list_active()
        return await self.supplier_repo.list_all()

    async def list_suppliers_with_count(self) -> List[dict]:
        """List suppliers with item counts."""
        return await self.supplier_repo.list_with_count()

    # =========================================================================
    # Purchase Order Management
    # =========================================================================

    async def create_purchase_order(self, data: CreatePurchaseOrder) -> PurchaseOrder:
        """Create a new purchase order."""
        # Validate supplier
        supplier = await self.supplier_repo.get(data.supplier_id)
        if not supplier:
            raise NotFoundError(f"Supplier {data.supplier_id} not found")

        # Generate PO number if not provided
        if not data.po_number:
            po_number = await self.po_repo.generate_po_number()
        else:
            po_number = data.po_number
            existing = await self.po_repo.get_by_number(po_number)
            if existing:
                raise ValidationError(
                    f"PO number '{po_number}' already exists")

        # Calculate total
        total_amount = Decimal(0)
        for item in data.items:
            total_amount += item.quantity * item.unit_price

        po_data = {
            "supplier_id": data.supplier_id,
            "po_number": po_number,
            "order_date": data.order_date or datetime.now(),
            "expected_delivery": data.expected_delivery,
            "status": "draft",
            "total_amount": total_amount,
            "notes": data.notes
        }

        po = await self.po_repo.create(po_data)

        # Create PO items
        for item_data in data.items:
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                item_id=item_data.item_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=item_data.quantity * item_data.unit_price,
                notes=item_data.notes
            )
            self.db.add(po_item)

        await self.db.flush()
        await self.db.refresh(po)
        return await self.po_repo.get_with_details(po.id)

    async def get_purchase_order(self, po_id: UUID) -> Optional[PurchaseOrder]:
        """Get purchase order by ID."""
        return await self.po_repo.get_with_details(po_id)

    async def get_purchase_order_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """Get purchase order by PO number."""
        return await self.po_repo.get_by_number(po_number)

    async def update_purchase_order_status(
        self,
        po_id: UUID,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[PurchaseOrder]:
        """Update purchase order status."""
        return await self.po_repo.update_status(po_id, status, notes)

    async def receive_purchase_order(
        self,
        po_id: UUID,
        received_items: Dict[UUID, Decimal],
        received_by: str
    ) -> Optional[PurchaseOrder]:
        """Receive items in a purchase order."""
        po = await self.po_repo.get_with_details(po_id)
        if not po:
            raise NotFoundError(f"Purchase order {po_id} not found")

        if po.status == "completed":
            raise BusinessError("Purchase order already completed")

        # Validate received quantities
        for item in po.items:
            if item.id in received_items:
                qty = received_items[item.id]
                if qty > item.quantity - item.received_quantity:
                    raise ValidationError(
                        f"Received quantity for {item.item.name} "
                        f"exceeds remaining quantity"
                    )

        return await self.po_repo.receive_order(po_id, received_items, received_by)

    async def generate_po_number(self) -> str:
        """Generate a unique PO number."""
        return await self.po_repo.generate_po_number()

    # =========================================================================
    # Dashboard & Analytics
    # =========================================================================

    async def get_statistics(self) -> dict:
        """Get inventory statistics."""
        return await self.item_repo.get_statistics()

    async def get_stock_alerts(self) -> List[dict]:
        """Get stock alerts."""
        items = await self.item_repo.get_low_stock_items()
        alerts = []

        for item in items:
            threshold = item.min_stock_threshold or Decimal(0)
            if item.current_stock <= 0:
                severity = "critical"
                status = "out_of_stock"
            elif threshold > 0 and item.current_stock <= (threshold / 2):
                severity = "critical"
                status = "critical"
            else:
                severity = "warning"
                status = "low"

            alerts.append({
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "current_stock": float(item.current_stock),
                "min_stock_threshold": float(threshold),
                "unit": item.unit,
                "status": status,
                "severity": severity
            })

        return alerts

    async def get_kpis(self) -> dict:
        """Get inventory KPIs."""
        total_skus = await self.item_repo.count()

        # Total inventory value
        stmt = select(
            func.sum(InventoryItem.current_stock * InventoryItem.cost_price)
        ).where(InventoryItem.status == InventoryStatus.ACTIVE)
        result = await self.db.execute(stmt)
        total_value = result.scalar() or Decimal(0)

        # Low stock items
        low_stock = len(await self.item_repo.get_low_stock_items())

        # Out of stock
        out_of_stock = await self.db.scalar(
            select(func.count(InventoryItem.id))
            .where(InventoryItem.status == InventoryStatus.OUT_OF_STOCK)
        ) or 0

        # Recent usage (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        usage_cost = await self.db.scalar(
            select(func.sum(InventoryMaterialUsage.total_cost))
            .where(InventoryMaterialUsage.used_at >= thirty_days_ago)
        ) or Decimal(0)

        return {
            "total_skus": total_skus,
            "total_inventory_value": float(total_value),
            "low_stock_items": low_stock,
            "out_of_stock_items": out_of_stock,
            "total_usage_cost": float(usage_cost)
        }

    # ============================================================================
    # Stock Alert Service Methods
    # ============================================================================

    async def get_active_alerts(self) -> List[StockAlert]:
        """Get all active stock alerts."""
        return await self.item_repo.get_active_alerts()

    async def get_critical_alerts(self) -> List[StockAlert]:
        """Get critical stock alerts."""
        return await self.item_repo.get_critical_alerts()

    async def resolve_alert(self, alert_id: UUID, resolved_by: str, note: Optional[str] = None) -> Optional[StockAlert]:
        """Resolve stock alert."""
        return await self.item_repo.resolve_alert(alert_id, resolved_by, note)

    async def check_stock_alerts(self) -> List[StockAlert]:
        """Check stock and create alerts if needed."""
        return await self.item_repo.check_and_create_alerts()

    async def get_stock_alerts_summary(self) -> dict:
        """Get summary of stock alerts."""
        active = await self.get_active_alerts()
        critical = await self.get_critical_alerts()

        return {
            "total_active": len(active),
            "critical": len(critical),
            "low_stock": len([a for a in active if a.alert_type == "low_stock"]),
            "out_of_stock": len([a for a in active if a.alert_type == "out_of_stock"]),
            "alerts": [StockAlertResponse.model_validate(a).model_dump() for a in active[:10]]
        }

    # ============================================================================
    # Stock Opname Service Methods
    # ============================================================================

    async def create_opname(self, data: StockOpnameCreate, performed_by: str) -> StockOpname:
        """Create stock opname."""
        opname_data = data.model_dump()
        opname_data["performed_by"] = performed_by
        return await self.item_repo.create_opname(opname_data)

    async def get_opnames(self, item_id: UUID) -> List[StockOpname]:
        """Get all opnames for an item."""
        return await self.item_repo.get_opnames(item_id)

    async def approve_opname(self, opname_id: UUID, approved_by: str) -> Optional[StockOpname]:
        """Approve stock opname."""
        opname = await self.item_repo.approve_opname(opname_id, approved_by)
        if opname:
            await self.db.flush()
        return opname
