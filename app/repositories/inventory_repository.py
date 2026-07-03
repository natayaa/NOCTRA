# repositories/inventory_repository.py
from __future__ import annotations

from uuid import UUID
from decimal import Decimal
from datetime import date

from sqlalchemy import select, delete, and_, or_, desc, func
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import List, Dict, Optional

from models.inventory import (
    InventoryItem, 
    InventoryMaterialUsage, 
    InventoryStockMovement,
    ProjectWorkshopTask,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem
)
from schemas.inventories import CreateInventoryItem, UpdateInventoryItem
from schemas.constants import StockMovementType, InventoryStatus


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, item_id: UUID) -> InventoryItem | None:
        stmt = select(InventoryItem).where(InventoryItem.id == item_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> InventoryItem | None:
        stmt = select(InventoryItem).where(InventoryItem.sku == sku)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_barcode(self, barcode: str) -> InventoryItem | None:
        stmt = select(InventoryItem).where(InventoryItem.barcode == barcode)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> InventoryItem | None:
        stmt = select(InventoryItem).where(InventoryItem.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self) -> list[InventoryItem]:
        stmt = select(InventoryItem).where(InventoryItem.status == InventoryStatus.ACTIVE)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_with_filters(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        low_stock_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[InventoryItem], int]:
        stmt = select(InventoryItem)
        count_stmt = select(func.count()).select_from(InventoryItem)

        filters = []
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
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.order_by(InventoryItem.name).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return items, total

    async def get_by_category(self, category: str) -> list[InventoryItem]:
        stmt = select(InventoryItem).where(InventoryItem.category == category)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_low_stock_items(self) -> list[InventoryItem]:
        stmt = select(InventoryItem).where(
            InventoryItem.current_stock <= InventoryItem.min_stock_threshold
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, payload: CreateInventoryItem) -> InventoryItem:
        item = InventoryItem(**payload.model_dump())
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update(self, item_id: UUID, payload: UpdateInventoryItem) -> InventoryItem | None:
        item = await self.get_by_id(item_id)
        if not item:
            return None

        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(item, key, value)

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update_stock(
        self, 
        item_id: UUID, 
        quantity: Decimal,
        movement_type: str,
        reference_type: str,
        reference_id: Optional[UUID] = None,
        note: Optional[str] = None,
        performed_by: Optional[str] = None
    ) -> InventoryItem | None:
        item = await self.get_by_id(item_id)
        if not item:
            return None

        previous_stock = item.current_stock
        
        if movement_type in [StockMovementType.PURCHASE, StockMovementType.RETURN]:
            item.current_stock += quantity
        elif movement_type in [StockMovementType.SALE, StockMovementType.USAGE, StockMovementType.WASTE]:
            if item.current_stock < quantity:
                raise ValueError(f"Insufficient stock. Current: {item.current_stock}, Required: {quantity}")
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
            performed_by=performed_by
        )
        self.db.add(movement)

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def soft_delete(self, item_id: UUID) -> bool:
        item = await self.get_by_id(item_id)
        if not item:
            return False

        item.status = InventoryStatus.INACTIVE
        await self.db.flush()
        return True

    async def get_stock_movements(
        self,
        item_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[InventoryStockMovement], int]:
        stmt = select(InventoryStockMovement)
        count_stmt = select(func.count()).select_from(InventoryStockMovement)

        if item_id:
            stmt = stmt.where(InventoryStockMovement.item_id == item_id)
            count_stmt = count_stmt.where(InventoryStockMovement.item_id == item_id)

        stmt = stmt.options(selectinload(InventoryStockMovement.item))
        stmt = stmt.order_by(desc(InventoryStockMovement.created_at)).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        movements = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return movements, total


class InventoryMaterialUsageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_project(self, project_id: UUID) -> List[InventoryMaterialUsage]:
        stmt = (
            select(InventoryMaterialUsage)
            .where(InventoryMaterialUsage.project_id == project_id)
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(InventoryMaterialUsage.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()
    
    async def get_by_job(self, job_id: UUID) -> List[InventoryMaterialUsage]:
        stmt = (
            select(InventoryMaterialUsage)
            .where(InventoryMaterialUsage.job_id == job_id)
            .options(selectinload(InventoryMaterialUsage.item))
            .order_by(InventoryMaterialUsage.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def create_usage_material(
        self, 
        usage: InventoryMaterialUsage,
        update_stock: bool = True
    ) -> InventoryMaterialUsage:
        self.db.add(usage)
        await self.db.flush()
        
        if update_stock:
            # Reduce stock
            inventory_repo = InventoryRepository(self.db)
            await inventory_repo.update_stock(
                item_id=usage.item_id,
                quantity=usage.quantity,
                movement_type=StockMovementType.USAGE,
                reference_type="material_usage",
                reference_id=usage.id,
                note=usage.note
            )
        
        await self.db.refresh(usage)
        return usage
    
    async def get_by_id(self, usage_id: UUID) -> InventoryMaterialUsage | None:
        stmt = select(InventoryMaterialUsage).where(InventoryMaterialUsage.id == usage_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def delete_usage_material(self, usage_id: UUID) -> bool:
        stmt = delete(InventoryMaterialUsage).where(InventoryMaterialUsage.id == usage_id)
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.rowcount > 0

    async def get_project_material_summary(self, project_id: UUID) -> dict:
        stmt = select(
            InventoryMaterialUsage.item_id,
            func.sum(InventoryMaterialUsage.quantity).label('total_quantity'),
            func.sum(InventoryMaterialUsage.total_cost).label('total_cost')
        ).where(
            InventoryMaterialUsage.project_id == project_id
        ).group_by(InventoryMaterialUsage.item_id)
        
        res = await self.db.execute(stmt)
        rows = res.all()
        
        return {
            "total_items": len(rows),
            "total_cost": sum(row.total_cost or 0 for row in rows),
            "items": rows
        }

    async def get_usage_by_period(
        self,
        start_date: date,
        end_date: date,
        item_id: Optional[UUID] = None
    ) -> List[InventoryMaterialUsage]:
        stmt = select(InventoryMaterialUsage).where(
            InventoryMaterialUsage.created_at >= start_date,
            InventoryMaterialUsage.created_at <= end_date
        )
        if item_id:
            stmt = stmt.where(InventoryMaterialUsage.item_id == item_id)
            
        stmt = stmt.options(selectinload(InventoryMaterialUsage.item))
        stmt = stmt.order_by(InventoryMaterialUsage.created_at.desc())
        
        res = await self.db.execute(stmt)
        return res.scalars().all()


class InventoryStockMovementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_stock_movement(self, data_object: InventoryStockMovement):
        self.db.add(data_object)
        await self.db.flush()
        return data_object
    
    async def recent_stock_movement(self, limit: int = 10):
        stmt = (
            select(
                InventoryStockMovement.id,
                InventoryStockMovement.type,
                InventoryStockMovement.quantity,
                InventoryStockMovement.previous_stock,
                InventoryStockMovement.new_stock,
                InventoryStockMovement.reference_type,
                InventoryStockMovement.reference_id,
                InventoryStockMovement.note,
                InventoryStockMovement.performed_by,
                InventoryItem.name.label("item_name"),
                InventoryItem.unit.label("unit"),
                InventoryStockMovement.created_at,
            )
            .join(InventoryItem, InventoryStockMovement.item_id == InventoryItem.id)
            .order_by(InventoryStockMovement.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        rows = res.all()
        
        return [
            {
                "id": str(row.id),
                "type": row.type,
                "quantity": float(row.quantity),
                "previous_stock": float(row.previous_stock),
                "new_stock": float(row.new_stock),
                "item_name": row.item_name,
                "unit": row.unit,
                "reference_type": row.reference_type,
                "reference_id": str(row.reference_id) if row.reference_id else None,
                "note": row.note,
                "performed_by": row.performed_by,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    
    async def get_by_item(self, item_id: UUID, limit: int = 50) -> List[InventoryStockMovement]:
        stmt = (
            select(InventoryStockMovement)
            .where(InventoryStockMovement.item_id == item_id)
            .order_by(InventoryStockMovement.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_summary_by_type(self, period_start: date, period_end: date) -> dict:
        stmt = select(
            InventoryStockMovement.type,
            func.sum(InventoryStockMovement.quantity).label('total_quantity')
        ).where(
            InventoryStockMovement.created_at >= period_start,
            InventoryStockMovement.created_at <= period_end
        ).group_by(InventoryStockMovement.type)
        
        res = await self.db.execute(stmt)
        rows = res.all()
        
        return {row.type: row.total_quantity for row in rows}


class ProjectWorkshopJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_project_workshop(self, job_id: UUID):
        stmt = (
            select(ProjectWorkshopTask)
            .where(ProjectWorkshopTask.id == job_id)
            .options(
                selectinload(ProjectWorkshopTask.material_usages)
                .selectinload(InventoryMaterialUsage.item)
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def get_by_project(self, project_id: UUID) -> ProjectWorkshopTask | None:
        stmt = (
            select(ProjectWorkshopTask)
            .where(ProjectWorkshopTask.project_id == project_id)
            .options(
                selectinload(ProjectWorkshopTask.material_usages)
                .selectinload(InventoryMaterialUsage.item)
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_history(self, object_data: ProjectWorkshopTask):
        self.db.add(object_data)
        await self.db.flush()
        await self.db.refresh(object_data)
        return object_data

    async def update(self, job_id: UUID, data: dict) -> ProjectWorkshopTask | None:
        job = await self.get_project_workshop(job_id)
        if not job:
            return None
            
        for key, value in data.items():
            if hasattr(job, key):
                setattr(job, key, value)
                
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def calculate_actual_cost(self, job_id: UUID) -> Decimal:
        job = await self.get_project_workshop(job_id)
        if not job:
            return Decimal(0)
            
        # Get material usage cost
        stmt = select(func.sum(InventoryMaterialUsage.total_cost)).where(
            InventoryMaterialUsage.job_id == job_id
        )
        res = await self.db.execute(stmt)
        material_cost = res.scalar() or Decimal(0)
        
        # Add labor cost (already in job.actual_cost)
        total_cost = job.actual_cost + material_cost
        
        # Update job actual cost
        job.actual_cost = total_cost
        await self.db.flush()
        
        return total_cost


class SupplierRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, supplier_data: dict) -> Supplier:
        supplier = Supplier(**supplier_data)
        self.db.add(supplier)
        await self.db.flush()
        await self.db.refresh(supplier)
        return supplier

    async def get_by_id(self, supplier_id: UUID) -> Supplier | None:
        return await self.db.get(Supplier, supplier_id)

    async def list_active(self) -> List[Supplier]:
        stmt = select(Supplier).where(Supplier.is_active == True)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def update(self, supplier_id: UUID, data: dict) -> Supplier | None:
        supplier = await self.get_by_id(supplier_id)
        if not supplier:
            return None
        for key, value in data.items():
            if hasattr(supplier, key):
                setattr(supplier, key, value)
        await self.db.flush()
        await self.db.refresh(supplier)
        return supplier


class PurchaseOrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, po_data: dict) -> PurchaseOrder:
        po = PurchaseOrder(**po_data)
        self.db.add(po)
        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def get_by_id(self, po_id: UUID) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.items)
                .selectinload(PurchaseOrderItem.item)
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_number(self, po_number: str) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(PurchaseOrder.po_number == po_number)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_with_filters(
        self,
        supplier_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[PurchaseOrder], int]:
        stmt = select(PurchaseOrder)
        count_stmt = select(func.count()).select_from(PurchaseOrder)

        filters = []
        if supplier_id:
            filters.append(PurchaseOrder.supplier_id == supplier_id)
        if status:
            filters.append(PurchaseOrder.status == status)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.options(selectinload(PurchaseOrder.supplier))
        stmt = stmt.order_by(desc(PurchaseOrder.created_at)).offset(offset).limit(limit)

        res = await self.db.execute(stmt)
        orders = res.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return orders, total