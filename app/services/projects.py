from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.projects import Project
from repositories.projects import ProjectRepository


class ProjectService:

    def __init__(self):
        self.repo = ProjectRepository()

    async def create(self, db: AsyncSession, payload: dict):
        project = Project(**payload)
        return await self.repo.create(db, project)

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