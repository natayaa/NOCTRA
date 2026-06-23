# services/inventory.py
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.inventory import InventoryItems
from models.inventory_workshop_jobs import WorkshopJob
from models.inventory_material_usage import JobMaterialUsage
from models.inventory_stock_movement import StockMovement
from models.price_list import PriceListItem
from models.projects import Project

from app.repositories.inventory_repository import InventoryRepository
from repositories.inventory_stock import StockMovementRepository  # asumsi ada


class InventoryService:
    """
    Service layer for inventory management.
    Handles stock movements, material consumption, and analytics.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.item_repo = InventoryRepository(db)
        self.stock_repo = StockMovementRepository(db)

    # -------------------------------------------------------------------------
    # Material Consumption (Core)
    # -------------------------------------------------------------------------

    async def consume_material(
        self,
        project_id: UUID,
        item_id: UUID,
        quantity: int,
        note: str | None = None,
    ) -> JobMaterialUsage:
        """
        Consume a material item for a project.
        Steps:
        1. Validate item and stock.
        2. Get or create WorkshopJob for the project.
        3. Deduct stock.
        4. Record material usage.
        5. Update project actual cost.
        6. Record stock movement.
        """
        # 1. Validate item and stock
        item = await self.item_repo.get(str(item_id))
        if not item:
            raise ValueError(f"Item with ID '{item_id}' not found")
        if item.current_stock < quantity:
            raise ValueError(
                f"Insufficient stock for '{item.name}'. "
                f"Available: {item.current_stock} {item.unit}"
            )

        # 2. Get project
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        # 3. Get or create WorkshopJob for the project
        job = await self._get_or_create_workshop_job(project)

        # 4. Determine unit price (from price list or item cost)
        unit_price = await self._get_material_unit_price(item)
        total_cost = Decimal(quantity) * unit_price

        # 5. Deduct stock
        item.current_stock -= quantity

        # 6. Record material usage
        usage = JobMaterialUsage(
            project_id=project.id,
            job_id=job.id,
            item_id=item.id,
            quantity=quantity,
            note=note,
        )
        self.db.add(usage)

        # 7. Update project actual cost
        project.actual_cost = (project.actual_cost or Decimal(0)) + total_cost

        # 8. Record stock movement
        movement = StockMovement(
            item_id=item.id,
            type="out",
            quantity=quantity,
            reference_type="project",
            reference_id=str(project_id),
            note=f"Used in {project.name}" + (f" - {note}" if note else ""),
        )
        self.db.add(movement)

        await self.db.flush()
        return usage

    async def _get_or_create_workshop_job(self, project: Project) -> WorkshopJob:
        """Retrieve existing WorkshopJob for a project or create a new one."""
        stmt = select(WorkshopJob).where(WorkshopJob.project_id == project.id)
        result = await self.db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            job = WorkshopJob(
                project_id=project.id,
                unit_name=project.name,
                status="active",
            )
            self.db.add(job)
            await self.db.flush()
        return job

    async def _get_material_unit_price(self,  item: InventoryItems) -> Decimal:
        """
        Fetch the current unit price for a material from the price list.
        Falls back to the item's cost price if not found in price list.
        """
        # Try to get from price list first
        stmt = (
            select(PriceListItem)
            .where(
                PriceListItem.name == item.name,
                PriceListItem.category == "material",
                PriceListItem.is_active == True,
            )
            .order_by(PriceListItem.effective_date.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        price_item = result.scalar_one_or_none()
        if price_item:
            return price_item.price
        else:
        # fallback ke cost_price dari inventory item
            return Decimal(str(item.cost_price))

        """# If not in price list, get cost price from inventory
        item = await self.item_repo.get_by_name(material_name)  # perlu method get_by_name
        if not item:
            raise ValueError(f"Material '{material_name}' not found in inventory")
        return item.cost_price"""
    
    
    async def use_item_for_job(
        self,
        project_id: str,
        item_id: str,
        quantity: int,
        note: str = None,
        job_id: str = None
    ) -> JobMaterialUsage:
        
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
    
        # Cek stok (bandingkan Decimal)
        if item.current_stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {item.current_stock} {item.unit}")
        
        # Kurangi stok
        item.current_stock -= quantity
        
        # Hitung total cost
        total_cost = quantity * Decimal(str(item.cost_price))
        
        # Validasi UUID
        try:
            project_uuid = UUID(project_id)
            item_uuid = UUID(item_id)
        except ValueError:
            raise ValueError("Invalid UUID format")

        # Cek item
        item = await self.item_repo.get(str(item_uuid))
        if not item:
            raise ValueError(f"Item with ID '{item_id}' not found")
        if item.current_stock < quantity:
            raise ValueError(
                f"Insufficient stock for '{item.name}'. "
                f"Available: {item.current_stock} {item.unit}"
            )

        # Kurangi stock
        item.current_stock -= quantity

        # Catat stock movement
        movement = StockMovement(
            item_id=item_uuid,
            type="out",
            quantity=quantity,
            reference_type="project",
            reference_id=project_uuid,
            note=note or f"Used for project {project_id}"
        )
        self.db.add(movement)

        # Buat material usage
        usage = JobMaterialUsage(
            project_id=project_uuid,
            item_id=item_uuid,
            quantity=quantity,
            note=note,
            job_id=job_id  # optional
        )
        self.db.add(usage)

        # Update project actual_cost
        project = await self.db.get(Project, project_uuid)
        if project:
            unit_price = await self._get_material_unit_price(item)
            total_cost = Decimal(quantity) * unit_price
            project.actual_cost = (project.actual_cost or Decimal(0)) + total_cost

        await self.db.flush()
        return usage

    # -------------------------------------------------------------------------
    # Labor Management
    # -------------------------------------------------------------------------

    async def add_labor_to_project(
        self,
        project_id: UUID,
        labor_type: str,
        hours: float,
    ) -> dict:
        """
        Add labor cost to a project based on price list.
        Updates project.actual_cost.
        """
        # 1. Get labor rate from price list
        price_item = await self._get_labor_price_from_list(labor_type)

        # 2. Get project
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        # 3. Calculate and update cost
        labor_cost = Decimal(str(hours)) * price_item.price
        project.actual_cost = (project.actual_cost or Decimal(0)) + labor_cost

        await self.db.flush()
        return {
            "labor_type": labor_type,
            "hours": hours,
            "rate_per_hour": price_item.price,
            "total_cost": labor_cost,
        }

    async def _get_labor_price_from_list(self, labor_type: str) -> PriceListItem:
        """Fetch the current rate for a labor type from the price list."""
        stmt = (
            select(PriceListItem)
            .where(
                PriceListItem.name.ilike(f"%{labor_type}%"),
                PriceListItem.category == "labor",
                PriceListItem.is_active == True,
            )
            .order_by(PriceListItem.effective_date.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        price_item = result.scalar_one_or_none()
        if not price_item:
            raise ValueError(f"Labor type '{labor_type}' not found in price list")
        return price_item

    # -------------------------------------------------------------------------
    # Analytics / Dashboard
    # -------------------------------------------------------------------------

    async def get_dashboard_kpis(self) -> dict:
        """Return key performance indicators for inventory dashboard."""
        # Total inventory value
        value_stmt = select(
            func.sum(InventoryItems.current_stock * InventoryItems.cost_price)
        )
        total_value = await self.db.execute(value_stmt)
        total_value = total_value.scalar() or 0

        # Total SKUs
        total_skus = await self.db.execute(select(func.count()).select_from(InventoryItems))
        total_skus = total_skus.scalar() or 0

        # Low stock count
        low_stmt = select(func.count()).where(
            InventoryItems.current_stock <= InventoryItems.min_stock_threshold
        )
        low_count = await self.db.execute(low_stmt)
        low_count = low_count.scalar() or 0

        return {
            "total_value": float(total_value),
            "total_skus": total_skus,
            "low_stock_count": low_count,
        }

    async def get_monthly_usage(self) -> dict:
        """Calculate total material usage cost in the last 30 days."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stmt = (
            select(func.sum(StockMovement.quantity * InventoryItems.cost_price))
            .join(InventoryItems)
            .where(
                StockMovement.type == "out",
                StockMovement.created_at >= thirty_days_ago,
            )
        )
        result = await self.db.execute(stmt)
        total = result.scalar() or 0
        return {"monthly_usage": float(total)}

    async def get_stock_alerts(self) -> list[dict]:
        """Return items with stock below or at threshold."""
        stmt = (
            select(InventoryItems)
            .where(
                InventoryItems.current_stock <= InventoryItems.min_stock_threshold,
                InventoryItems.status == "active",
            )
            .order_by(InventoryItems.current_stock.asc())
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        alerts = []
        for item in items:
            critical = item.current_stock <= (item.min_stock_threshold // 2)
            alerts.append({
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_stock": item.current_stock,
                "min_stock_threshold": item.min_stock_threshold,
                "status": "critical" if critical else "low",
            })
        return alerts

    async def get_recent_movements(self, limit: int = 5) -> list[dict]:
        """Return most recent stock movements with enriched item names."""
        stmt = (
            select(StockMovement)
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        movements = result.scalars().all()

        data = []
        for m in movements:
            item = await self.db.get(InventoryItems, m.item_id)
            data.append({
                "id": m.id,
                "type": m.type,
                "quantity": m.quantity,
                "item_name": item.name if item else "Unknown",
                "note": m.note,
                "created_at": m.created_at,
            })
        return data
    
    async def get_by_name(self, name: str) -> InventoryItems | None:
        stmt = select(InventoryItems).where(InventoryItems.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()