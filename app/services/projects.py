from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal
from datetime import datetime

from models.projects import Project, ProjectLabor
from models.inventory_workshop_jobs import WorkshopJob
from models.price_list import PriceListItem
from repositories.projects import ProjectRepository
from repositories.customer_inquiry import InquiryRepo
from schemas.constants import InquiryStatus

class ProjectService:
    def __init__(self):
        self.repo = ProjectRepository()

    async def create(self, db: AsyncSession, payload: dict):
        project = Project(**payload)
        db.add(project)
        await db.flush()

        # Auto-create WorkshopJob untuk project ini
        job = WorkshopJob(
            project_id=project.id,
            unit_name=project.name,
            status="active",
            estimated_cost=project.estimated_cost or 0
        )
        db.add(job)
        await db.flush()

        return project
    
    async def get_project_with_financials(self, db: AsyncSession, project_id: str):
        project = await self.repo.get(db, project_id)
        if not project:
            return None

        # Hitung total material cost dari workshop_job
        material_cost = Decimal(0)
        if project.workshop_job:
            for usage in project.workshop_job.material_usages:
                if usage.item:
                    material_cost += usage.quantity * usage.item.cost_price

        # Total labor cost
        labor_cost = sum([l.total_cost for l in project.labor_items], Decimal(0))

        actual_cost = material_cost + labor_cost + (project.actual_cost or Decimal(0))
        actual_revenue = project.actual_revenue or Decimal(0)
        profit = actual_revenue - actual_cost
        margin = (profit / actual_revenue * 100) if actual_revenue else Decimal(0)

        # Siapkan data tambahan
        return {
            "project": project,
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "actual_cost": actual_cost,
            "profit": profit,
            "margin": margin,
            "material_usages": project.workshop_job.material_usages if project.workshop_job else [],
            "labor_items": project.labor_items,
        }

    async def add_labor(self, db: AsyncSession, project_id: str, labor_type: str, hours: Decimal, rate_per_hour: Decimal = None):
        # Jika rate tidak diberikan, ambil dari price list
        if rate_per_hour is None:
            # Cari price list dengan category 'labor' dan name = labor_type
            stmt = select(PriceListItem).where(
                PriceListItem.category == 'labor',
                PriceListItem.name == labor_type,
                PriceListItem.is_active == True
            ).order_by(PriceListItem.effective_date.desc()).limit(1)
            result = await db.execute(stmt)
            price_item = result.scalar_one_or_none()
            if not price_item:
                raise ValueError(f"Labor type '{labor_type}' not found in price list")
            rate_per_hour = price_item.price

        total_cost = hours * rate_per_hour
        labor = ProjectLabor(
            project_id=project_id,
            labor_type=labor_type,
            hours=hours,
            rate_per_hour=rate_per_hour,
            total_cost=total_cost
        )
        db.add(labor)
        await db.flush()
        return labor

    async def get_labor_list(self, db: AsyncSession, project_id: str):
        project = await self.repo.get(db, project_id)
        return project.labor_items if project else []

    async def delete_labor(self, db: AsyncSession, labor_id: str):
        labor = await db.get(ProjectLabor, labor_id)
        if not labor:
            return False
        await db.delete(labor)
        await db.flush()
        return True
    
    async def kanban(self, db: AsyncSession):
        result = await db.execute(select(Project))
        projects = result.scalars().all()

        board = {
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": []
        }

        for p in projects:
            status = (p.status or "todo").lower()

            # safety mapping biar tidak crash kalau data aneh
            if status not in board:
                status = "todo"

            board[status].append(self._serialize_project(p))

        return board

    def _serialize_project(self, p: Project):
        return {
            "id": p.id,
            "inquiry_id": p.inquiry_id,
            "name": p.name,
            "customer_name": p.customer_name,
            "vehicle_brand": p.vehicle_brand,
            "vehicle_model": p.vehicle_model,
            "status": p.status,
            "progress": p.progress or 0,
            "estimated_cost": float(p.estimated_cost or 0),
            "actual_cost": float(p.actual_cost or 0),
            "estimated_revenue": float(p.estimated_revenue or 0),
            "actual_revenue": float(p.actual_revenue or 0),
        }

    async def revenue_summary(self, db: AsyncSession):
        result = await db.execute(
            select(
                func.sum(Project.actual_revenue),
                func.sum(Project.actual_cost)
            )
        )

        revenue, cost = result.one()

        return {
            "total_revenue": float(revenue or 0),
            "total_cost": float(cost or 0),
            "profit": float((revenue or 0) - (cost or 0))
        }
        
    async def complete_project(self, db: AsyncSession, project_id: str):
        project = await self.repo.get(db, project_id)
        if not project:
            raise ValueError("Project not found")
        project.status = "completed"
        project.progress = 100
        project.completed_at = datetime.now()
        # Hitung actual cost otomatis
        project.actual_cost = await self.calculate_actual_cost(db, project_id)
        await db.flush()
        # Kirim notifikasi (WA/email)
        await self.send_completion_notification(project)
        return project
    
    async def complete_project(self, db: AsyncSession, project_id: str):
        project = await self.repo.get(db, project_id)
        if not project:
            raise ValueError("Project not found")
        project.status = "completed"
        project.progress = 100
        project.completed_at = datetime.now()

        # Jika project memiliki inquiry_id, update status inquiry menjadi completed
        if project.inquiry_id:
            inquiry_repo = InquiryRepo(db)
            inquiry = await inquiry_repo.get(project.inquiry_id)
            if inquiry and inquiry.status != InquiryStatus.COMPLETED:
                inquiry.status = InquiryStatus.COMPLETED
                await inquiry_repo.add_activity(
                    project.inquiry_id,
                    f"Project completed: {project.name}"
                )

        await db.flush()
        return project