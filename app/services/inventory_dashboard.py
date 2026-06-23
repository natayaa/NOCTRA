# services/inventory_dashboard.py
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

# Model (diperlukan untuk query SQLAlchemy)
from models.inventory import (
    InventoryItem,
    InventoryStockMovement,
    InventoryMaterialUsage,
    ProjectWorkshopTask,
)
from models.projects import Project
from models.price_list import PriceListItem

# Repository yang tersedia
from repositories.inventory_repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,   # typo diperbaiki
    ProjectWorkshopJobRepository,
)


# ============================================================================
# 1. DASHBOARD SERVICE (tidak banyak berubah, hanya perbaikan import & repo)
# ============================================================================
class InventoryDashboardService:
    """
    Service for inventory dashboard analytics.
    Provides KPIs, stock alerts, usage statistics, and movement insights.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        # Repository tidak selalu dipakai, tapi disimpan untuk kemungkinan perlu
        self.inventory_item_repo = InventoryRepository(db)
        self.inventory_stock_repo = InventoryStockMovementRepository(db)

    # ----------------------------------------------------------------------
    # Key Performance Indicators
    # ----------------------------------------------------------------------
    async def get_kpis(self) -> dict:
        active_filter = InventoryItem.status == "active"

        total_skus = await self.db.scalar(
            select(func.count(InventoryItem.id)).where(active_filter)
        )

        total_value = await self.db.scalar(
            select(func.sum(InventoryItem.current_stock * InventoryItem.cost_price))
            .where(active_filter)
        )

        low_stock = await self.db.scalar(
            select(func.count(InventoryItem.id))
            .where(
                active_filter,
                InventoryItem.current_stock <= InventoryItem.min_stock_threshold,
            )
        )

        return {
            "total_skus": total_skus or 0,
            "total_inventory_value": float(total_value or Decimal(0)),
            "low_stock_items": low_stock or 0,
        }

    # ----------------------------------------------------------------------
    # Stock Alerts
    # ----------------------------------------------------------------------
    async def get_stock_alerts(self) -> list[dict]:
        stmt = select(InventoryItem).where(
            InventoryItem.status == "active",
            InventoryItem.current_stock <= InventoryItem.min_stock_threshold,
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        alerts = []
        for item in items:
            threshold = item.min_stock_threshold or Decimal(0)
            critical = threshold > 0 and item.current_stock <= (threshold / Decimal(2))
            alerts.append(
                {
                    "id": str(item.id),
                    "name": item.name,
                    "category": item.category,
                    "current_stock": float(item.current_stock),
                    "min_stock_threshold": float(threshold),
                    "status": "critical" if critical else "low",
                }
            )
        return alerts

    # ----------------------------------------------------------------------
    # Usage Statistics (based on Stock Movements)
    # ----------------------------------------------------------------------
    async def get_monthly_usage(self) -> list[dict]:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        stmt = (
            select(
                InventoryItem.id,
                InventoryItem.name,
                func.coalesce(
                    func.sum(InventoryStockMovement.quantity), Decimal(0)
                ).label("used_quantity"),
            )
            .join(InventoryItem, InventoryStockMovement.item_id == InventoryItem.id)
            .where(
                InventoryStockMovement.type == "out",
                InventoryStockMovement.created_at >= thirty_days_ago,
            )
            .group_by(InventoryItem.id, InventoryItem.name)
            .order_by(func.sum(InventoryStockMovement.quantity).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "item_id": str(row.id),
                "item_name": row.name,
                "used_quantity": float(row.used_quantity or 0),
            }
            for row in rows
        ]

    async def get_top_used_items(self, days: int = 30, limit: int = 10) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                InventoryItem.id,
                InventoryItem.name,
                func.coalesce(
                    func.sum(InventoryStockMovement.quantity), Decimal(0)
                ).label("total_used"),
            )
            .join(InventoryItem, InventoryStockMovement.item_id == InventoryItem.id)
            .where(
                InventoryStockMovement.type == "out",
                InventoryStockMovement.created_at >= since,
            )
            .group_by(InventoryItem.id, InventoryItem.name)
            .order_by(func.sum(InventoryStockMovement.quantity).desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "item_id": str(row.id),
                "item_name": row.name,
                "total_used": float(row.total_used or 0),
            }
            for row in rows
        ]

    # ----------------------------------------------------------------------
    # Inventory Value by Category
    # ----------------------------------------------------------------------
    async def get_inventory_value_by_category(self) -> list[dict]:
        stmt = (
            select(
                InventoryItem.category,
                func.coalesce(
                    func.sum(InventoryItem.current_stock * InventoryItem.cost_price),
                    Decimal(0),
                ).label("total_value"),
                func.count(InventoryItem.id).label("item_count"),
            )
            .where(InventoryItem.status == "active")
            .group_by(InventoryItem.category)
            .order_by(
                func.sum(InventoryItem.current_stock * InventoryItem.cost_price).desc()
            )
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "category": row.category or "Uncategorized",
                "total_value": float(row.total_value or 0),
                "item_count": row.item_count or 0,
            }
            for row in rows
        ]

    # ----------------------------------------------------------------------
    # Recent Stock Movements
    # ----------------------------------------------------------------------
    async def get_recent_movements(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(
                InventoryStockMovement.id,
                InventoryStockMovement.type,
                InventoryStockMovement.quantity,
                InventoryItem.name.label("item_name"),
                InventoryStockMovement.created_at,
            )
            .join(InventoryItem, InventoryStockMovement.item_id == InventoryItem.id)
            .order_by(InventoryStockMovement.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "id": row.id,
                "type": row.type,
                "quantity": float(row.quantity),
                "item_name": row.item_name,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    # ----------------------------------------------------------------------
    # Usage per Project (using InventoryMaterialUsage)
    # ----------------------------------------------------------------------
    async def get_usage_by_project(self, project_id: UUID) -> list[dict]:
        stmt = (
            select(
                InventoryMaterialUsage,
                InventoryItem.name.label("item_name"),
            )
            .join(InventoryItem, InventoryMaterialUsage.item_id == InventoryItem.id)
            .where(InventoryMaterialUsage.project_id == project_id)
            .order_by(InventoryMaterialUsage.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "usage_id": row.InventoryMaterialUsage.id,
                "item_id": row.InventoryMaterialUsage.item_id,
                "item_name": row.item_name,
                "quantity_used": float(row.InventoryMaterialUsage.quantity),
                "note": row.InventoryMaterialUsage.note,
                "created_at": row.InventoryMaterialUsage.created_at.isoformat()
                if row.InventoryMaterialUsage.created_at
                else None,
            }
            for row in rows
        ]


# ============================================================================
# 2. INVENTORY SERVICES (untuk transaksi konsumsi material)
# ============================================================================
class InventoryServices:
    """
    Layanan untuk operasi bisnis inventory (konsumsi material, dll.)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_repo = InventoryRepository(db)
        self.usage_repo = InventoryMaterialUsageRepository(db)
        self.stock_movement_repo = InventoryStockMovementRepository(db)
        self.workshop_repo = ProjectWorkshopJobRepository(db)

    async def inventory_consume_material(
        self,
        project_id: UUID,
        item_id: UUID,
        quantity: int,
        note: str | None = None,
    ) -> InventoryMaterialUsage:
        """
        Konsumsi material untuk suatu project.
        Langkah:
            1. Validasi item dan stok
            2. Dapatkan atau buat WorkshopJob untuk project (jika belum ada)
            3. Kurangi stok item
            4. Catat pemakaian material (InventoryMaterialUsage)
            5. (Opsional) Update actual cost project
            6. Catat pergerakan stok (InventoryStockMovement)
        """
        # 1. Validasi item dan stok
        item = await self.inventory_repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Item dengan ID {item_id} tidak ditemukan")
        if item.current_stock < quantity:
            raise ValueError(
                f"Stok tidak mencukupi. Tersedia: {item.current_stock}, diminta: {quantity}"
            )

        # 2. Dapatkan atau buat WorkshopJob untuk project
        #    Asumsi: ada relasi project -> workshop task, kita coba cari berdasarkan project_id
        #    Jika belum ada, buat baru (dengan data minimal)
        #    Catatan: di repository hanya ada get_project_workshop(job_id) – mungkin perlu method tambahan.
        #    Untuk sementara kita asumsikan selalu ada, atau kita buat sederhana: cari berdasarkan project_id
        #    (Kita perlu menambahkan method di repository atau query langsung)
        #    Karena di repository tidak ada get_by_project, kita lakukan query manual.
        stmt = select(ProjectWorkshopTask).where(
            ProjectWorkshopTask.project_id == project_id
        )
        result = await self.db.execute(stmt)
        workshop_job = result.scalar_one_or_none()

        if not workshop_job:
            # Buat WorkshopTask baru (misal dengan nama default)
            # Di sini kita perlu field yang diperlukan; asumsikan ada minimal.
            workshop_job = ProjectWorkshopTask(
                project_id=project_id,
                name=f"Workshop for project {project_id}",
                status="active",
            )
            self.db.add(workshop_job)
            await self.db.flush()  # dapatkan ID

        # 3. Kurangi stok item
        item.current_stock -= quantity
        await self.db.flush()

        # 4. Catat pemakaian material
        usage = InventoryMaterialUsage(
            project_id=project_id,
            item_id=item_id,
            quantity=quantity,
            note=note,
            workshop_job_id=workshop_job.id,  # opsional, jika ada relasi
        )
        usage = await self.usage_repo.create_usage_material(usage)

        # 5. (Opsional) Update actual cost project
        #    Misal: project.actual_cost += quantity * item.cost_price
        #    Tidak diimplementasikan di sini karena tidak ada model Project di file ini.

        # 6. Catat pergerakan stok (out)
        movement = InventoryStockMovement(
            item_id=item_id,
            type="out",
            quantity=quantity,
            # reference_id bisa diisi dengan usage.id atau project_id
            reference_id=usage.id,
            note=f"Material consumed for project {project_id}",
        )
        await self.stock_movement_repo.create_stock_movement(self.db, movement)

        return usage
    
    async def _get_or_create_workshop_jobs(self, project: Project) -> ProjectWorkshopTask:
        stmt = select(ProjectWorkshopTask).where(ProjectWorkshopTask.project_id == project.id)
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()
        
        if not job:
            job = ProjectWorkshopTask(
                project_id=project.id,
                unit_name=project.name,
                status="active"
            )
            self.db.add(job)
            await self.db.flush()
            
        return job
    
    async def _get_material_unit_price(self, item: InventoryItem) -> Decimal:
        """
            Fetch the current unit price for a material from the price list
            falls back to the item's cost price if not found in the price list
        """
        statement = (
            select(PriceListItem)
            .where(
                PriceListItem.name == item.name,
                PriceListItem.category == "material",
                PriceListItem.is_active == True
            )
            .order_by(PriceListItem.effective_date.desc())
            .limit(1)
        )
        res = await self.db.execute(statement)
        price_item = res.scalar_one_or_none()
        if price_item:
            return price_item.price
        else:
            # fallback ke cost_price dari inventory item
            return Decimal(str(item.cost_price))
        
    async def use_item_for_job(self, proeject_id: str, item_id: str, quantity: int, note: str = None, job_id: str = None) -> InventoryMaterialUsage:
        try:
            project_uuid = UUID(proeject_id)
            item_uuid = UUID(item_id)
        except ValueError:
            raise ValueError("Invalid UUID Format for Project/Item")
        
        # check item 
        item = await self.inventory_repo.get_by_id(item_id=str(item_id))
        if not item:
            raise ValueError(f"Item with ID : {item_id} not found")
        if item.current_stock < quantity:
            raise ValueError(f"Insufficient stock for '{item.name}. Available stock : {item.current_stock} {item.unit}")
        
        # kurangin stock
        item.current_stock -= quantity
        movement = InventoryStockMovement(
            item_id=item_uuid,
            type="out",
            quantity=quantity,
            reference_type="project",
            reference_id=project_uuid,
            note=note or f"Used for project {project_uuid}"
        )
        self.db.add(movement)
        
        # buat material usage
        materialusage = InventoryMaterialUsage(
            proeject_id=project_uuid,
            item_id=item_uuid,
            quantity=quantity,
            note=note,
            job_id=job_id
        )
        self.db.add(materialusage)
        
        # update project actual_cost
        project = await self.db.get(Project, project_uuid)
        if project: 
            unit_price = await self._get_material_unit_price(item)
            total_cost = Decimal(quantity) * unit_price
            project.actual_cost = (project.actual_cost or Decimal(0)) + total_cost
            
        await self.db.flush()
        
        return materialusage
    
    # labor management
    async def add_labor_to_project(self, project_id: UUID, labor_type: str, hours: float) -> Dict:
        """
            Add labor cost to a project based on price list
            updates project.actual_cost
        """
        # 1. get labor rate from price list
        price_item = await self._get_labor_price_from_list(labor_type)
        # 2. get project
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project with ID : {project_id} not found")
        # 3. Calculate and update costt
        labot_cost = Decimal(str(hours)) * price_item.price
        project.actual_cost = (project.actual_cost or Decimal(0)) + labot_cost
        
        await self.db.flush()
        return {
            "labor_type": labor_type,
            "hours": hours, "rate_per_hour": price_item.price, "total_cost": labot_cost
        }
        
    async def _get_labor_price_from_list(self, labor_type: str) -> PriceListItem:
        """Fetch the current rate for a labor type from the price list"""
        stmt = (
            select(PriceListItem)
            .where(
                PriceListItem.name.ilike(f"%{labor_type}%"),
                PriceListItem.category == "labor",
                PriceListItem.is_active == True
            )
            .order_by(PriceListItem.effective_date.desc())
            .limit(1)
        )
        
        result = await self.db.execute(stmt)
        price_item = result.scalar_one_or_none()
        if not price_item:
            raise ValueError(f"Labor type '{labor_type}' not found in the price list")
        
        return price_item
    
    