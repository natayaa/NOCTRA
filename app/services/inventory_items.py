# services/inventory.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import HTTPException
from uuid import UUID
from decimal import Decimal

from models.inventory_items import InventoryItems
from models.inventory_workshop_jobs import WorkshopJob
from models.inventory_material_usage import JobMaterialUsage
from models.inventory_stock_movement import StockMovement
from models.price_list import PriceListItem
from models.projects import Project
from repositories.inventory_items import InventoryRepository
#from repositories.inventory_stock immport stock
from schemas.inventory_material_usage import MaterialUsageCreate


class InventoryService:
    def __init__(self, db):
        self.db = db
        self.repo = InventoryRepository(db)          # tambahkan ini
        #self.stock_repo = StockMovementRepository()  # atau sesuaikan

    @staticmethod
    async def consume_material(db: AsyncSession, usage: MaterialUsageCreate):
        # 1. Get item
        item = await db.get(InventoryItems, usage.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.current_stock < usage.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Available: {item.current_stock} {item.unit}"
            )

        # 2. Get project
        project = await db.get(Project, usage.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 3. Get or create workshop job for this project
        stmt = select(WorkshopJob).where(
            WorkshopJob.project_id == usage.project_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            job = WorkshopJob(
                project_id=usage.project_id,
                unit_name=project.name,
                status="active"
            )
            db.add(job)
            await db.flush()

        # 4. Deduct stock
        item.current_stock -= usage.quantity

        # 5. Record usage
        material_usage = JobMaterialUsage(
            job_id=job.id,
            item_id=usage.item_id,
            quantity=usage.quantity,
            note=usage.note
        )
        db.add(material_usage)

        # 6. Update project actual cost (material cost)
        material_cost = Decimal(str(usage.quantity)) * \
            Decimal(str(item.cost_price))
        project.actual_cost = (
            project.actual_cost or Decimal(0)) + material_cost

        # 7. Record stock movement
        movement = StockMovement(
            item_id=usage.item_id,
            type="out",
            quantity=usage.quantity,
            reference_type="project",
            reference_id=str(usage.project_id),
            note=f"Used in {project.name}" +
            (f" - {usage.note}" if usage.note else "")
        )
        db.add(movement)

        await db.flush()
        return material_usage

    @staticmethod
    async def get_dashboard_kpis(db: AsyncSession):
        # total value
        total_value_stmt = select(
            func.sum(InventoryItems.current_stock * InventoryItems.cost_price))
        total_value = await db.execute(total_value_stmt)
        total_value = total_value.scalar() or 0

        # total SKUs
        total_skus_stmt = select(func.count()).select_from(InventoryItems)
        total_skus = await db.execute(total_skus_stmt)
        total_skus = total_skus.scalar() or 0

        # low stock count
        low_stmt = select(func.count()).where(
            InventoryItems.current_stock <= InventoryItems.min_stock_threshold
        )
        low_count = await db.execute(low_stmt)
        low_count = low_count.scalar() or 0

        return {
            "total_value": float(total_value),
            "total_skus": total_skus,
            "low_stock_count": low_count
        }

    @staticmethod
    async def get_monthly_usage(db: AsyncSession):
        # For simplicity, we'll sum all out movements in the last 30 days.
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stmt = select(func.sum(StockMovement.quantity * InventoryItems.cost_price))\
            .join(InventoryItems)\
            .where(
            StockMovement.type == "out",
            StockMovement.created_at >= thirty_days_ago
        )
        result = await db.execute(stmt)
        total = result.scalar() or 0
        return {"monthly_usage": float(total)}

    @staticmethod
    async def get_stock_alerts(db: AsyncSession):
        stmt = select(InventoryItems).where(
            InventoryItems.current_stock <= InventoryItems.min_stock_threshold,
            InventoryItems.status == "active"
        ).order_by(InventoryItems.current_stock.asc())
        result = await db.execute(stmt)
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
                "status": "critical" if critical else "low"
            })
        return alerts

    @staticmethod
    async def get_recent_movements(db: AsyncSession, limit: int = 5):
        stmt = select(StockMovement).order_by(
            StockMovement.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        movements = result.scalars().all()
        # enrich with item name
        data = []
        for m in movements:
            item = await db.get(InventoryItems, m.item_id)
            data.append({
                "id": m.id,
                "type": m.type,
                "quantity": m.quantity,
                "item_name": item.name if item else "Unknown",
                "note": m.note,
                "created_at": m.created_at
            })
        return

    # services/inventory.py

    async def consume_material_for_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        item_id: UUID,
        quantity: int,
        note: str = None
    ):
        # 1. Ambil item dari inventory
        item = await db.get(InventoryItems, item_id)
        if not item:
            raise ValueError("Item not found")
        if item.current_stock < quantity:
            raise ValueError(
                f"Stok tidak cukup. Tersisa: {item.current_stock}")

        # 2. Ambil project
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")

        # 3. Ambil WorkshopJob untuk project ini
        job = await db.execute(
            select(WorkshopJob).where(WorkshopJob.project_id == project_id)
        )
        job = job.scalar_one_or_none()
        if not job:
            job = WorkshopJob(project_id=project_id,
                              unit_name=project.name, status="active")
            db.add(job)
            await db.flush()

        # 4. Ambil harga dari Price List (jika ada)
        price_list_item = await db.execute(
            select(PriceListItem).where(
                PriceListItem.name == item.name,
                PriceListItem.category == "material",
                PriceListItem.is_active == True
            )
        )
        price_list_item = price_list_item.scalar_one_or_none()

        # Kalau ada di Price List, pakai harganya. Kalau tidak, pakai cost_price dari inventory.
        unit_price = price_list_item.price if price_list_item else item.cost_price
        total_cost = quantity * unit_price

        # 5. Kurangi stock
        item.current_stock -= quantity

        # 6. Catat material usage
        usage = JobMaterialUsage(
            job_id=job.id,
            item_id=item.id,
            quantity=quantity,
            note=note
        )
        db.add(usage)

        # 7. Update project actual_cost
        project.actual_cost = (project.actual_cost or 0) + total_cost

        # 8. Catat stock movement
        movement = StockMovement(
            item_id=item.id,
            type="out",
            quantity=quantity,
            reference_type="project",
            reference_id=str(project_id),
            note=f"Digunakan untuk {project.name}" +
            (f" - {note}" if note else "")
        )
        db.add(movement)

        await db.flush()
        return usage

    async def add_labor_to_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        labor_type: str,  # misal "painter", "body_repair", "assembly"
        hours: float
    ):
        # 1. Ambil harga labor dari Price List
        price_item = await db.execute(
            select(PriceListItem).where(
                PriceListItem.name.ilike(f"%{labor_type}%"),
                PriceListItem.category == "labor",
                PriceListItem.is_active == True
            )
        )
        price_item = price_item.scalar_one_or_none()
        if not price_item:
            raise ValueError(
                f"Labor type '{labor_type}' not found in Price List")

        # 2. Ambil project
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")

        # 3. Hitung total labor cost
        labor_cost = price_item.price * hours

        # 4. Update project
        project.labor_cost = (project.labor_cost or 0) + labor_cost
        project.actual_cost = (project.actual_cost or 0) + labor_cost

        await db.flush()
        return {"labor_type": labor_type, "hours": hours, "cost": labor_cost}


    # ... dalam method use_item_for_job
    async def use_item_for_job(self, project_id: str, item_id: str, quantity: int, note: str = None, job_id: str = None):
        item = await self.repo.get(item_id)
        if not item:
            raise ValueError("Item not found")
        if item.current_stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {item.current_stock}")

        item.current_stock -= quantity

        # Konversi project_id ke UUID
        try:
            project_uuid = UUID(project_id)
        except ValueError:
            raise ValueError("Invalid project_id format")

        # Catat stock movement (pastikan item_id juga UUID)
        movement = StockMovement(
            item_id=UUID(item_id),  # jika item_id string, konversi juga
            type="out",
            quantity=quantity,
            reference_type="project",
            reference_id=project_uuid,   # ← pakai UUID, bukan string
            note=note
        )
        self.db.add(movement)

        # Buat material usage
        usage = JobMaterialUsage(
            project_id=project_uuid,   # ← pakai UUID juga
            item_id=UUID(item_id),
            quantity=quantity,
            note=note,
            job_id=job_id
        )
        self.db.add(usage)
        await self.db.flush()
        return usage
