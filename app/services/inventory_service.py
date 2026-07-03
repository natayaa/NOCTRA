# services/inventory.py
from decimal import Decimal
from uuid import UUID
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.inventory import InventoryItem, InventoryMaterialUsage, InventoryStockMovement
from models.projects import Project
from models.price_list import PriceListItem
from repositories.inventory_repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,
)
from schemas.constants import StockMovementType


class InventoryService:
    """
    Service untuk operasi bisnis inventory.
    Menangani konsumsi material, pergerakan stock, dan operasi inventory lainnya.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_repo = InventoryRepository(db)
        self.usage_repo = InventoryMaterialUsageRepository(db)
        self.stock_movement_repo = InventoryStockMovementRepository(db)

    async def _get_material_unit_price(self, item: InventoryItem) -> Decimal:
        """
        Fetch the current unit price for a material from the price list.
        Falls back to the item's cost price if not found in the price list.
        """
        from sqlalchemy import select
        
        stmt = (
            select(PriceListItem)
            .where(
                PriceListItem.name == item.name,
                PriceListItem.category == "material",
                PriceListItem.is_active == True
            )
            .order_by(PriceListItem.effective_date.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        price_item = res.scalar_one_or_none()
        
        if price_item:
            return price_item.price
        else:
            # fallback ke cost_price dari inventory item
            return Decimal(str(item.cost_price))

    async def _get_or_create_workshop_job(self, project_id: UUID) -> Any:
        """Get or create workshop job for a project."""
        from models.inventory import ProjectWorkshopTask
        from sqlalchemy import select
        
        stmt = select(ProjectWorkshopTask).where(ProjectWorkshopTask.project_id == project_id)
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()
        
        if not job:
            # Get project name
            project = await self.db.get(Project, project_id)
            job = ProjectWorkshopTask(project_id=project_id, unit_name=project.name if project else f"Project {project_id}", status="active")
            self.db.add(job)
            await self.db.flush()
            
        return job

    async def use_item_for_job(self, project_id: UUID, item_id: UUID, quantity: Decimal, note: Optional[str] = None, job_id: Optional[UUID] = None) -> InventoryMaterialUsage:
        """
        Consume an item for a project/job.
        
        Args:
            project_id: ID of the project
            item_id: ID of the inventory item
            quantity: Quantity to consume
            note: Optional note
            job_id: Optional workshop job ID
            
        Returns:
            InventoryMaterialUsage instance
        """
        # Validate item and stock
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")
        
        if item.current_stock < quantity:
            raise ValueError(
                f"Insufficient stock for '{item.name}'. "
                f"Available: {item.current_stock} {item.unit}, "
                f"Required: {quantity} {item.unit}"
            )

        # Get or create workshop job if not provided
        if not job_id:
            job = await self._get_or_create_workshop_job(project_id)
            job_id = job.id

        # Get unit price
        unit_price = await self._get_material_unit_price(item)
        total_cost = Decimal(str(quantity)) * unit_price

        # Create material usage
        usage = InventoryMaterialUsage(project_id=project_id, job_id=job_id, item_id=item_id,  quantity=quantity, unit_cost=unit_price, total_cost=total_cost, note=note)
        self.db.add(usage)

        # Update stock
        previous_stock = item.current_stock
        item.current_stock -= quantity
        
        # Update status if out of stock
        if item.current_stock <= 0:
            item.status = "out_of_stock"

        # Create stock movement
        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.USAGE,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=item.current_stock,
            reference_type="project",
            reference_id=project_id,
            note=note or f"Used for project {project_id}",
            performed_by="system"
        )
        self.db.add(movement)

        # Update project actual cost
        project = await self.db.get(Project, project_id)
        if project:
            project.actual_cost = (project.actual_cost or Decimal(0)) + total_cost

        await self.db.flush()
        await self.db.refresh(usage)
        
        return usage
    
    async def _convert_quantity(
        self, 
        item: InventoryItem, 
        quantity: Decimal, 
        from_unit: Optional[str] = None
    ) -> Decimal:
        """
        Konversi quantity ke unit item.
        Jika from_unit tidak diberikan, asumsikan sudah dalam unit item.
        """
        if from_unit is None or from_unit == item.unit:
            return quantity
        
        # 🔥 Konversi dari ml ke liter
        if from_unit.lower() == 'ml' and item.unit.lower() == 'liter':
            return quantity / Decimal('1000')
        # Konversi dari liter ke ml
        elif from_unit.lower() == 'liter' and item.unit.lower() == 'ml':
            return quantity * Decimal('1000')
        # Konversi dari gram ke kg
        elif from_unit.lower() == 'gram' and item.unit.lower() == 'kg':
            return quantity / Decimal('1000')
        # Konversi dari kg ke gram
        elif from_unit.lower() == 'kg' and item.unit.lower() == 'gram':
            return quantity * Decimal('1000')
        # Konversi menggunakan conversion_factor
        elif item.base_unit and item.conversion_factor and item.conversion_factor > 0:
            return quantity / item.conversion_factor
        
        # Jika tidak ada konversi yang dikenal, raise error
        raise ValueError(
            f"Tidak bisa konversi dari {from_unit} ke {item.unit}. "
            f"Pastikan item memiliki base_unit dan conversion_factor yang benar."
        )
    
    async def use_item_for_job(
        self,
        project_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        unit: Optional[str] = None,
        note: Optional[str] = None,
        job_id: Optional[UUID] = None
    ) -> InventoryMaterialUsage:
        """
        Consume an item for a project/job.
        """
        # Validate item
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")
        
        # 🔥 DEBUG: Log untuk debugging
        # print(f"🔍 Item: {item.name}, Unit: {item.unit}, Stock: {item.current_stock}")
        # print(f"🔍 Request: {quantity} {unit if unit else item.unit}")
        
        # 🔥 Konversi quantity ke unit item
        if unit and unit != item.unit:
            quantity_in_item_unit = await self._convert_quantity(item, quantity, unit)
        else:
            quantity_in_item_unit = quantity
        
        print(f"🔍 Converted: {quantity_in_item_unit} {item.unit}")
        
        # Check stock (dalam unit item)
        if item.current_stock < quantity_in_item_unit:
            raise ValueError(
                f"Stok tidak mencukupi untuk '{item.name}'. "
                f"Tersedia: {float(item.current_stock):.3f} {item.unit}, "
                f"Dibutuhkan: {float(quantity_in_item_unit):.3f} {item.unit} "
                f"(dari {float(quantity):.3f} {unit if unit else item.unit})"
            )
        
        # Get or create workshop job
        if not job_id:
            job = await self._get_or_create_workshop_job(project_id)
            job_id = job.id
        
        # Calculate cost based on quantity in item unit
        unit_price = await self._get_material_unit_price(item)
        total_cost = quantity_in_item_unit * unit_price
        
        # 🔥 Buat usage object
        usage = InventoryMaterialUsage(
            project_id=project_id,
            job_id=job_id,
            item_id=item_id,
            quantity=quantity_in_item_unit,
            unit_cost=unit_price,
            total_cost=total_cost,
            note=note or f"Digunakan: {float(quantity):.3f} {unit if unit else item.unit}"
        )
        self.db.add(usage)
        
        # Update stock (dalam unit item)
        previous_stock = item.current_stock
        item.current_stock -= quantity_in_item_unit
        
        # Create stock movement
        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.USAGE,
            quantity=quantity_in_item_unit,
            previous_stock=previous_stock,
            new_stock=item.current_stock,
            reference_type="project",
            reference_id=project_id,
            note=f"Digunakan: {float(quantity):.3f} {unit if unit else item.unit} - {note or ''}",
            performed_by="system"
        )
        self.db.add(movement)
        
        # Update project actual cost
        project = await self.db.get(Project, project_id)
        if project:
            project.actual_cost = (project.actual_cost or Decimal(0)) + total_cost
        
        # 🔥 FLUSH dan REFRESH untuk mendapatkan ID
        await self.db.flush()
        await self.db.refresh(usage)  # 🔥 PENTING: Refresh untuk mendapatkan ID
        
        # 🔥 Debug: Pastikan usage memiliki ID
        # print(f"✅ Usage created with ID: {usage.id}")
        
        return usage  # 🔥 PASTIKAN RETURN
        

    async def add_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: Optional[UUID] = None,
        note: Optional[str] = None,
        performed_by: Optional[str] = None
    ) -> InventoryStockMovement:
        """
        Add stock to an item (purchase, return, etc.).
        """
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")

        previous_stock = item.current_stock
        item.current_stock += quantity
        
        # Update status if was out of stock
        if item.status == "out_of_stock" and item.current_stock > 0:
            item.status = "active"

        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.PURCHASE,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=item.current_stock,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note or f"Stock added: {quantity} {item.unit}",
            performed_by=performed_by or "system"
        )
        self.db.add(movement)
        await self.db.flush()
        await self.db.refresh(movement)
        
        return movement

    async def adjust_stock(
        self,
        item_id: UUID,
        new_quantity: Decimal,
        reason: str,
        performed_by: Optional[str] = None
    ) -> InventoryStockMovement:
        """
        Adjust stock to a specific quantity (for physical count corrections).
        """
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")

        previous_stock = item.current_stock
        quantity = new_quantity - previous_stock
        item.current_stock = new_quantity

        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.ADJUSTMENT,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=item.current_stock,
            reference_type="adjustment",
            reference_id=None,
            note=f"Stock adjustment: {reason}",
            performed_by=performed_by or "system"
        )
        self.db.add(movement)
        await self.db.flush()
        await self.db.refresh(movement)
        
        return movement

    async def transfer_stock(
        self,
        item_id: UUID,
        quantity: Decimal,
        from_location: str,
        to_location: str,
        note: Optional[str] = None,
        performed_by: Optional[str] = None
    ) -> InventoryStockMovement:
        """
        Transfer stock between locations.
        """
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")
        
        if item.current_stock < quantity:
            raise ValueError(
                f"Insufficient stock for transfer. "
                f"Available: {item.current_stock} {item.unit}, "
                f"Required: {quantity} {item.unit}"
            )

        # Update location
        item.location = to_location

        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.TRANSFER,
            quantity=quantity,
            previous_stock=item.current_stock,
            new_stock=item.current_stock,
            reference_type="transfer",
            reference_id=None,
            note=note or f"Transferred from {from_location} to {to_location}",
            performed_by=performed_by or "system"
        )
        self.db.add(movement)
        await self.db.flush()
        await self.db.refresh(movement)
        
        return movement

    async def record_waste(
        self,
        item_id: UUID,
        quantity: Decimal,
        reason: str,
        performed_by: Optional[str] = None
    ) -> InventoryMaterialUsage:
        """
        Record wasted/damaged material.
        """
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")
        
        if item.current_stock < quantity:
            raise ValueError(
                f"Insufficient stock to record waste. "
                f"Available: {item.current_stock} {item.unit}, "
                f"Required: {quantity} {item.unit}"
            )

        previous_stock = item.current_stock
        item.current_stock -= quantity

        # Create material usage with waste flag
        usage = InventoryMaterialUsage(
            project_id=None,
            job_id=None,
            item_id=item_id,
            quantity=quantity,
            unit_cost=item.cost_price,
            total_cost=quantity * item.cost_price,
            note=f"Waste: {reason}",
            is_waste=True,
            waste_percentage=Decimal(100)
        )
        self.db.add(usage)

        # Create stock movement
        movement = InventoryStockMovement(
            item_id=item_id,
            type=StockMovementType.WASTE,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=item.current_stock,
            reference_type="waste",
            reference_id=None,
            note=f"Waste recorded: {reason}",
            performed_by=performed_by or "system"
        )
        self.db.add(movement)

        await self.db.flush()
        await self.db.refresh(usage)
        
        return usage

    async def get_item_details(self, item_id: UUID) -> Dict[str, Any]:
        """
        Get detailed information about an item including usage history.
        """
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")

        # Get recent usages
        usages = await self.usage_repo.get_by_project(item_id)  # This needs to be fixed

        # Get recent movements
        movements = await self.stock_movement_repo.get_by_item(item_id, limit=20)

        return {
            "item": item,
            "recent_usages": usages[:10] if usages else [],
            "recent_movements": movements if movements else []
        }