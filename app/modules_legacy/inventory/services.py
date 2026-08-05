# modules/inventory/services.py
"""
Inventory Service - REFACTORED

✅ Clear separation of concerns: Item, Stock, Material Usage, Workshop, Supplier, PO
✅ Integration dengan Project, Price List, Payment
✅ Soft delete support
✅ Stock movement tracking with audit trail
✅ Transaction handling di setiap method
✅ Lazy import untuk menghindari circular dependency
"""

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
from .repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,
    ProjectWorkshopJobRepository,
    SupplierRepository,
    PurchaseOrderRepository
)
from .schemas import (
    CreateInventoryItem,
    UpdateInventoryItem,
    CreateInventoryMaterialUsage,
    CreateInventoryStockMovement,
    CreatePurchaseOrder,
    CreateSupplier,
    StockAlertResponse,
    StockOpnameCreate,
    StockOpnameUpdate,
    StockOpnameResponse,
    UpdateSupplier,
)

# TYPE_CHECKING untuk menghindari circular import
if TYPE_CHECKING:
    from modules.project.repository import ProjectRepository
    from modules.price_list.repository import PriceListRepository


class InventoryService:
    """
    Service untuk Inventory management.
    
    ✅ Handle transaction di setiap method
    ✅ Lazy import untuk menghindari circular dependency
    ✅ Semua operasi Decimal dengan benar
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.item_repo = InventoryRepository(db)
        self.usage_repo = InventoryMaterialUsageRepository(db)
        self.movement_repo = InventoryStockMovementRepository(db)
        self.workshop_repo = ProjectWorkshopJobRepository(db)
        self.supplier_repo = SupplierRepository(db)
        self.po_repo = PurchaseOrderRepository(db)
        
        # Lazy loaded repositories
        self._project_repo = None
        self._price_list_repo = None

    # =========================================================================
    # Repository Accessors (Lazy import untuk menghindari circular)
    # =========================================================================

    @property
    def project_repo(self):
        """Lazy import untuk ProjectRepository."""
        if self._project_repo is None:
            from modules.project.repository import ProjectRepository
            self._project_repo = ProjectRepository(self.db)
        return self._project_repo

    @property
    def price_list_repo(self):
        """Lazy import untuk PriceListRepository."""
        if self._price_list_repo is None:
            from modules.price_list.repository import PriceListRepository
            self._price_list_repo = PriceListRepository(self.db)
        return self._price_list_repo

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _to_decimal(self, value) -> Decimal:
        """Safe conversion to Decimal."""
        if value is None:
            return Decimal('0')
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            return Decimal(value)
        return Decimal('0')

    def _calculate_available_stock(self, item: InventoryItem) -> Decimal:
        """Calculate available stock (current - reserved)."""
        return item.current_stock - item.reserved_stock

    def _determine_status(self, current_stock: Decimal, min_threshold: Decimal) -> str:
        """Determine inventory status based on stock level."""
        if current_stock <= 0:
            return InventoryStatus.OUT_OF_STOCK
        elif current_stock <= min_threshold:
            return InventoryStatus.LOW_STOCK
        return InventoryStatus.ACTIVE

    # =========================================================================
    # ITEM MANAGEMENT
    # =========================================================================

    async def create_item(self, data: CreateInventoryItem) -> InventoryItem:
        """Create a new inventory item."""
        try:
            # Check SKU uniqueness
            if data.sku:
                existing = await self.item_repo.get_by_sku(data.sku)
                if existing:
                    raise ValidationError(f"SKU '{data.sku}' already exists")

            # Check barcode uniqueness
            if data.barcode:
                existing = await self.item_repo.get_by_barcode(data.barcode)
                if existing:
                    raise ValidationError(f"Barcode '{data.barcode}' already exists")

            # Validate supplier exists
            if data.supplier_id:
                supplier = await self.supplier_repo.get(data.supplier_id)
                if not supplier:
                    raise NotFoundError(f"Supplier {data.supplier_id} not found")

            # Validate price list item exists
            if data.price_list_item_id:
                price_item = await self.price_list_repo.get(data.price_list_item_id)
                if not price_item:
                    raise NotFoundError(f"Price list item {data.price_list_item_id} not found")

            # Prepare data with auto-calculated status
            item_data = data.model_dump()
            current_stock = self._to_decimal(item_data.get('current_stock', 0))
            min_threshold = self._to_decimal(item_data.get('min_stock_threshold', 0))
            reserved_stock = self._to_decimal(item_data.get('reserved_stock', 0))

            item_data['status'] = self._determine_status(current_stock, min_threshold)
            item_data['available_stock'] = current_stock - reserved_stock

            # Create item
            item = InventoryItem(**item_data)
            self.db.add(item)
            await self.db.flush()
            await self.db.refresh(item)

            # Add initial stock movement if current_stock > 0
            if current_stock > 0:
                movement = InventoryStockMovement(
                    item_id=item.id,
                    type=StockMovementType.ADJUSTMENT,
                    quantity=current_stock,
                    previous_stock=Decimal('0'),
                    new_stock=current_stock,
                    reference_type="initial_stock",
                    note="Initial stock entry",
                    performed_by="system"
                )
                self.db.add(movement)
                await self.db.flush()

            return item

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_item(self, item_id: UUID) -> Optional[InventoryItem]:
        """Get inventory item by ID."""
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
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[InventoryItem], int]:
        """List inventory items with filters."""
        return await self.item_repo.list_with_filters(
            category=category,
            status=status,
            search=search,
            low_stock_only=low_stock_only,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset
        )

    async def update_item(
        self,
        item_id: UUID,
        data: UpdateInventoryItem
    ) -> Optional[InventoryItem]:
        """Update inventory item."""
        try:
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
                    raise ValidationError(f"Barcode '{data.barcode}' already exists")

            # Validate supplier if updating
            if data.supplier_id and data.supplier_id != item.supplier_id:
                supplier = await self.supplier_repo.get(data.supplier_id)
                if not supplier:
                    raise NotFoundError(f"Supplier {data.supplier_id} not found")

            # Validate price list item if updating
            if data.price_list_item_id and data.price_list_item_id != item.price_list_item_id:
                price_item = await self.price_list_repo.get(data.price_list_item_id)
                if not price_item:
                    raise NotFoundError(f"Price list item {data.price_list_item_id} not found")

            # Auto-update status if stock changed
            if 'current_stock' in update_data:
                current_stock = self._to_decimal(update_data['current_stock'])
                min_threshold = self._to_decimal(update_data.get('min_stock_threshold', item.min_stock_threshold))
                update_data['status'] = self._determine_status(current_stock, min_threshold)
                update_data['available_stock'] = current_stock - item.reserved_stock

            # Update item
            item = await self.item_repo.update(item_id, update_data)
            await self.db.flush()
            await self.db.refresh(item)

            return item

        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_item(self, item_id: UUID) -> bool:
        """Soft delete inventory item."""
        try:
            result = await self.item_repo.delete(item_id)
            await self.db.flush()
            return result
        except ValueError as e:
            await self.db.rollback()
            raise BusinessError(str(e))
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return await self.item_repo.get_categories()

    # =========================================================================
    # STOCK MANAGEMENT
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
        try:
            item = await self.item_repo.get(item_id)
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            valid_types = [t.value for t in StockMovementType]
            if movement_type not in valid_types:
                raise ValidationError(f"Invalid movement type: {movement_type}")

            # Validate stock sufficiency for negative movements
            qty = self._to_decimal(quantity)
            if movement_type in [StockMovementType.USAGE, StockMovementType.WASTE, StockMovementType.SALE]:
                if item.current_stock < qty:
                    raise ValidationError(
                        f"Insufficient stock. Available: {item.current_stock} {item.unit}, "
                        f"Required: {qty} {item.unit}"
                    )

            # Update stock
            updated_item = await self.item_repo.update_stock(
                item_id=item_id,
                quantity=qty,
                movement_type=movement_type,
                reference_type=reference_type,
                reference_id=reference_id,
                note=note,
                performed_by=performed_by
            )

            if not updated_item:
                raise NotFoundError(f"Item {item_id} not found")

            await self.db.flush()
            await self.db.refresh(updated_item)

            # Get the movement record (last created)
            movements = await self.movement_repo.get_by_item(item_id, limit=1)
            if not movements:
                raise ValidationError("Failed to create stock movement")

            return movements[0]

        except Exception as e:
            await self.db.rollback()
            raise e

    async def reserve_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID,
        performed_by: Optional[str] = None
    ) -> InventoryItem:
        """Reserve stock for a project or job."""
        try:
            qty = self._to_decimal(quantity)
            item = await self.item_repo.reserve_stock(
                item_id=item_id,
                quantity=qty,
                reference_type=reference_type,
                reference_id=reference_id
            )
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            await self.db.flush()
            await self.db.refresh(item)
            return item

        except ValueError as e:
            await self.db.rollback()
            raise ValidationError(str(e))
        except Exception as e:
            await self.db.rollback()
            raise e

    async def release_reserved_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID
    ) -> InventoryItem:
        """Release reserved stock."""
        try:
            qty = self._to_decimal(quantity)
            item = await self.item_repo.release_reserved_stock(
                item_id=item_id,
                quantity=qty,
                reference_type=reference_type,
                reference_id=reference_id
            )
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            await self.db.flush()
            await self.db.refresh(item)
            return item

        except ValueError as e:
            await self.db.rollback()
            raise ValidationError(str(e))
        except Exception as e:
            await self.db.rollback()
            raise e

    # =========================================================================
    # MATERIAL USAGE
    # =========================================================================

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
        try:
            qty = self._to_decimal(quantity)
            if qty <= 0:
                raise ValidationError("Quantity must be greater than 0")

            item = await self.item_repo.get(item_id)
            if not item:
                raise NotFoundError(f"Item {item_id} not found")

            # Check stock
            if item.current_stock < qty:
                raise ValidationError(
                    f"Insufficient stock. Available: {item.current_stock} {item.unit}, "
                    f"Required: {qty} {item.unit}"
                )

            # Get or create workshop job
            if not job_id:
                job = await self._get_or_create_workshop_job(project_id)
                job_id = job.id

            # Create material usage
            usage = await self.usage_repo.create_usage(
                item_id=item_id,
                quantity=qty,
                project_id=project_id,
                job_id=job_id,
                note=note,
                is_waste=is_waste,
                confirmed_by=confirmed_by
            )

            # Update inventory stock via repository
            await self.item_repo.update_stock(
                item_id=item_id,
                quantity=qty,
                movement_type=StockMovementType.USAGE,
                reference_type="material_usage",
                reference_id=usage.id,
                note=f"Material used for {'project' if project_id else 'job'}",
                performed_by=confirmed_by
            )

            # Update project actual cost
            try:
                project = await self.project_repo.get(project_id)
                if project:
                    project.actual_cost = (project.actual_cost or Decimal(0)) + usage.total_cost
                    await self.project_repo.add_activity(
                        project_id,
                        f"Material consumed: {item.name} x {qty} {item.unit}",
                        "material_consumption",
                        performed_by=confirmed_by or "system"
                    )
            except Exception as e:
                # Project module may not be available, log but continue
                pass

            await self.db.flush()
            await self.db.refresh(usage)
            return usage

        except Exception as e:
            await self.db.rollback()
            raise e

    async def _get_or_create_workshop_job(
        self,
        project_id: UUID
    ) -> ProjectWorkshopTask:
        """Get or create workshop job for a project."""
        job = await self.workshop_repo.get_by_project(project_id)
        if not job:
            # Try to get project name
            project_name = f"Project {project_id}"
            estimated_cost = Decimal(0)

            try:
                project = await self.project_repo.get(project_id)
                if project:
                    project_name = project.name or project_name
                    estimated_cost = project.estimated_cost or Decimal(0)
            except Exception:
                pass

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

    async def get_material_usages_by_project(
        self,
        project_id: UUID
    ) -> List[InventoryMaterialUsage]:
        """Get all material usages for a project."""
        return await self.usage_repo.get_by_project(project_id)

    # =========================================================================
    # STOCK MOVEMENTS
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
    # WORKSHOP JOBS
    # =========================================================================

    async def get_workshop_job(self, project_id: UUID) -> Optional[ProjectWorkshopTask]:
        """Get workshop job for a project."""
        return await self.workshop_repo.get_by_project(project_id)

    async def get_workshop_job_by_id(self, job_id: UUID) -> Optional[ProjectWorkshopTask]:
        """Get workshop job by ID."""
        return await self.workshop_repo.get_with_materials(job_id)

    async def update_workshop_job_status(
        self,
        job_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[ProjectWorkshopTask]:
        """Update workshop job status."""
        try:
            job = await self.workshop_repo.update_status(job_id, status, note)
            if job and job.project_id:
                try:
                    await self.project_repo.add_activity(
                        job.project_id,
                        f"Workshop job status updated: {status}",
                        "workshop_update",
                        performed_by="system"
                    )
                except Exception:
                    pass

            await self.db.flush()
            await self.db.refresh(job) if job else None
            return job

        except Exception as e:
            await self.db.rollback()
            raise e

    async def calculate_workshop_cost(self, job_id: UUID) -> Decimal:
        """Calculate total cost for a workshop job."""
        try:
            cost = await self.workshop_repo.calculate_actual_cost(job_id)
            await self.db.flush()
            return cost
        except Exception as e:
            await self.db.rollback()
            raise e

    # =========================================================================
    # SUPPLIER MANAGEMENT
    # =========================================================================

    async def create_supplier(self, data: CreateSupplier) -> Supplier:
        """Create a new supplier."""
        try:
            supplier = Supplier(**data.model_dump())
            self.db.add(supplier)
            await self.db.flush()
            await self.db.refresh(supplier)
            return supplier
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_supplier(self, supplier_id: UUID) -> Optional[Supplier]:
        """Get supplier by ID."""
        return await self.supplier_repo.get_with_details(supplier_id)

    async def list_suppliers(self, active_only: bool = True) -> List[Supplier]:
        """List all suppliers."""
        if active_only:
            return await self.supplier_repo.list_active()
        return await self.supplier_repo.get_all()

    async def list_suppliers_with_count(self) -> List[dict]:
        """List suppliers with item counts."""
        return await self.supplier_repo.list_with_count()

    async def update_supplier(
        self,
        supplier_id: UUID,
        data: UpdateSupplier
    ) -> Optional[Supplier]:
        """Update supplier."""
        try:
            supplier = await self.supplier_repo.update(
                supplier_id,
                data.model_dump(exclude_unset=True)
            )
            if supplier:
                await self.db.flush()
                await self.db.refresh(supplier)
            return supplier
        except Exception as e:
            await self.db.rollback()
            raise e

    # =========================================================================
    # PURCHASE ORDER MANAGEMENT
    # =========================================================================

    async def create_purchase_order(self, data: CreatePurchaseOrder) -> PurchaseOrder:
        """Create a new purchase order."""
        try:
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
                    raise ValidationError(f"PO number '{po_number}' already exists")

            # Validate items and calculate total
            total_amount = Decimal(0)
            for item_data in data.items:
                inventory_item = await self.item_repo.get(item_data.item_id)
                if not inventory_item:
                    raise NotFoundError(f"Item {item_data.item_id} not found")
                total_amount += item_data.quantity * item_data.unit_price

            # Create PO
            po_data = {
                "supplier_id": data.supplier_id,
                "po_number": po_number,
                "order_date": data.order_date or datetime.now(),
                "expected_delivery": data.expected_delivery,
                "status": "draft",
                "total_amount": total_amount,
                "notes": data.notes
            }

            po = PurchaseOrder(**po_data)
            self.db.add(po)
            await self.db.flush()
            await self.db.refresh(po)

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

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_purchase_order(self, po_id: UUID) -> Optional[PurchaseOrder]:
        """Get purchase order by ID."""
        return await self.po_repo.get_with_details(po_id)

    async def get_purchase_order_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """Get purchase order by PO number."""
        return await self.po_repo.get_by_number(po_number)

    async def list_purchase_orders_by_supplier(
        self,
        supplier_id: UUID,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[PurchaseOrder]:
        """List purchase orders by supplier."""
        return await self.po_repo.list_by_supplier(supplier_id, status, limit)

    async def update_purchase_order_status(
        self,
        po_id: UUID,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[PurchaseOrder]:
        """Update purchase order status."""
        try:
            po = await self.po_repo.update_status(po_id, status, notes)
            if po:
                await self.db.flush()
                await self.db.refresh(po)
            return po
        except Exception as e:
            await self.db.rollback()
            raise e

    async def receive_purchase_order(
        self,
        po_id: UUID,
        received_items: Dict[UUID, Decimal],
        received_by: str
    ) -> Optional[PurchaseOrder]:
        """Receive items in a purchase order."""
        try:
            po = await self.po_repo.receive_order(po_id, received_items, received_by)
            if not po:
                raise NotFoundError(f"Purchase order {po_id} not found")

            await self.db.flush()
            await self.db.refresh(po)
            return po

        except ValueError as e:
            await self.db.rollback()
            raise ValidationError(str(e))
        except Exception as e:
            await self.db.rollback()
            raise e

    async def generate_po_number(self) -> str:
        """Generate a unique PO number."""
        return await self.po_repo.generate_po_number()

    # =========================================================================
    # DASHBOARD & ANALYTICS
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
        ).where(
            InventoryItem.status == InventoryStatus.ACTIVE,
            InventoryItem.is_deleted == False
        )
        result = await self.db.execute(stmt)
        total_value = result.scalar() or Decimal(0)

        # Low stock items
        low_stock = len(await self.item_repo.get_low_stock_items())

        # Out of stock
        out_of_stock = await self.db.scalar(
            select(func.count(InventoryItem.id))
            .where(
                InventoryItem.status == InventoryStatus.OUT_OF_STOCK,
                InventoryItem.is_deleted == False
            )
        ) or 0

        # Recent usage (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        usage_cost = await self.db.scalar(
            select(func.sum(InventoryMaterialUsage.total_cost))
            .where(
                InventoryMaterialUsage.used_at >= thirty_days_ago,
                InventoryMaterialUsage.is_deleted == False
            )
        ) or Decimal(0)

        return {
            "total_skus": total_skus,
            "total_inventory_value": float(total_value),
            "low_stock_items": low_stock,
            "out_of_stock_items": out_of_stock,
            "total_usage_cost": float(usage_cost)
        }

    # =========================================================================
    # STOCK ALERT SERVICE METHODS
    # =========================================================================

    async def get_active_alerts(self) -> List[StockAlert]:
        """Get all active stock alerts."""
        return await self.item_repo.get_active_alerts()

    async def get_critical_alerts(self) -> List[StockAlert]:
        """Get critical stock alerts."""
        return await self.item_repo.get_critical_alerts()

    async def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by: str,
        note: Optional[str] = None
    ) -> Optional[StockAlert]:
        """Resolve stock alert."""
        try:
            alert = await self.item_repo.resolve_alert(alert_id, resolved_by, note)
            if alert:
                await self.db.flush()
                await self.db.refresh(alert)
            return alert
        except Exception as e:
            await self.db.rollback()
            raise e

    async def check_stock_alerts(self) -> List[StockAlert]:
        """Check stock and create alerts if needed."""
        try:
            alerts = await self.item_repo.check_and_create_alerts()
            await self.db.flush()
            return alerts
        except Exception as e:
            await self.db.rollback()
            raise e

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

    # =========================================================================
    # STOCK OPNAME SERVICE METHODS
    # =========================================================================

    async def create_opname(
        self,
        data: StockOpnameCreate,
        performed_by: str
    ) -> StockOpname:
        """Create stock opname."""
        try:
            opname_data = data.model_dump()
            opname_data["performed_by"] = performed_by
            opname = await self.item_repo.create_opname(opname_data)
            await self.db.flush()
            await self.db.refresh(opname)
            return opname
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_opnames(self, item_id: UUID) -> List[StockOpname]:
        """Get all opnames for an item."""
        return await self.item_repo.get_opnames(item_id)

    async def approve_opname(
        self,
        opname_id: UUID,
        approved_by: str
    ) -> Optional[StockOpname]:
        """Approve stock opname."""
        try:
            opname = await self.item_repo.approve_opname(opname_id, approved_by)
            if opname:
                await self.db.flush()
                await self.db.refresh(opname)
            return opname
        except Exception as e:
            await self.db.rollback()
            raise e