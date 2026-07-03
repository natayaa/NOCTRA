# repositories/projects.py
from uuid import UUID
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from models.projects import (
    Project, 
    ProjectTask, 
    ProjectExpense, 
    ProjectLabor, 
    ProjectActivity,
    ProjectStage
)
from models.inventory import (
    InventoryMaterialUsage,
    ProjectWorkshopTask
)
from models.customer_inquiry import CustomerInquiry
from schemas.constants import ProjectStatus


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # CREATE
    # ============================================================
    
    async def create(self, obj: Project) -> Project:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    # ============================================================
    # READ
    # ============================================================
    
    async def get(self, project_id: UUID) -> Project | None:
        result = await self.db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.inquiry).selectinload(CustomerInquiry.photos),
                selectinload(Project.tasks),
                selectinload(Project.expense_items),
                selectinload(Project.project_expenses),
                selectinload(Project.labor_items),
                selectinload(Project.workshop_job)
                    .selectinload(ProjectWorkshopTask.material_usages)
                    .selectinload(InventoryMaterialUsage.item),
                selectinload(Project.activities),
                selectinload(Project.stage),
            )
        )
        return result.scalar_one_or_none()

    async def get_basic(self, project_id: UUID) -> Project | None:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        brand: Optional[str] = None,
        search: Optional[str] = None,
        is_archived: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Project], int]:
        stmt = select(Project)
        count_stmt = select(func.count()).select_from(Project)

        filters = [Project.is_archived == is_archived]
        
        if status:
            filters.append(Project.status == status)
        if priority:
            filters.append(Project.priority == priority)
        if brand:
            filters.append(Project.vehicle_brand == brand)
        if search:
            filters.append(
                or_(
                    Project.name.ilike(f"%{search}%"),
                    Project.customer_name.ilike(f"%{search}%"),
                    Project.vehicle_brand.ilike(f"%{search}%"),
                    Project.vehicle_model.ilike(f"%{search}%"),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.options(
            selectinload(Project.inquiry),
            selectinload(Project.stage),
        )
        stmt = stmt.order_by(desc(Project.created_at)).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return projects, total

    # ============================================================
    # UPDATE
    # ============================================================

    async def update(self, project_id: UUID, data: Dict[str, Any]) -> Project | None:
        project = await self.get(project_id)
        if not project:
            return None
        
        for key, value in data.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)
        
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def update_status(
        self,
        project_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Project | None:
        project = await self.get(project_id)
        if not project:
            return None
        project.status = status
        if note:
            project.notes = note
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def update_progress(self, project_id: UUID, progress: int) -> Project | None:
        project = await self.get(project_id)
        if not project:
            return None
        project.progress = progress
        await self.db.flush()
        await self.db.refresh(project)
        return project

    # ============================================================
    # DELETE
    # ============================================================

    async def delete(self, project_id: UUID) -> bool:
        result = await self.db.execute(
            delete(Project).where(Project.id == project_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def archive(self, project_id: UUID) -> bool:
        project = await self.get(project_id)
        if not project:
            return False
        project.is_archived = True
        await self.db.flush()
        return True

    async def unarchive(self, project_id: UUID) -> bool:
        project = await self.get(project_id)
        if not project:
            return False
        project.is_archived = False
        await self.db.flush()
        return True

    # ============================================================
    # ACTIVITIES
    # ============================================================

    async def add_activity(
        self,
        project_id: UUID,
        activity: str,
        activity_type: Optional[str] = None,
        performed_by: Optional[str] = None,
        meta_data: Optional[Dict] = None
    ) -> ProjectActivity:
        activity_obj = ProjectActivity(
            project_id=project_id,
            activity=activity,
            activity_type=activity_type,
            performed_by=performed_by,
            meta_data=meta_data
        )
        self.db.add(activity_obj)
        await self.db.flush()
        await self.db.refresh(activity_obj)
        return activity_obj

    async def get_activities(self, project_id: UUID) -> List[ProjectActivity]:
        stmt = select(ProjectActivity).where(
            ProjectActivity.project_id == project_id
        ).order_by(desc(ProjectActivity.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # TASKS
    # ============================================================

    async def add_task(self, project_id: UUID, task_data: Dict[str, Any]) -> ProjectTask:
        task = ProjectTask(project_id=project_id, **task_data)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_tasks(self, project_id: UUID) -> List[ProjectTask]:
        stmt = select(ProjectTask).where(
            ProjectTask.project_id == project_id
        ).order_by(ProjectTask.sort_order)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_task(self, task_id: UUID, data: Dict[str, Any]) -> ProjectTask | None:
        stmt = select(ProjectTask).where(ProjectTask.id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            return None
        
        for key, value in data.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)
        
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete_task(self, task_id: UUID) -> bool:
        result = await self.db.execute(
            delete(ProjectTask).where(ProjectTask.id == task_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ============================================================
    # EXPENSES
    # ============================================================

    async def add_expense(self, project_id: UUID, expense_data: Dict[str, Any]) -> ProjectExpense:
        expense = ProjectExpense(project_id=project_id, **expense_data)
        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def get_expenses(self, project_id: UUID) -> List[ProjectExpense]:
        stmt = select(ProjectExpense).where(
            ProjectExpense.project_id == project_id
        ).order_by(desc(ProjectExpense.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_expense(self, expense_id: UUID) -> bool:
        result = await self.db.execute(
            delete(ProjectExpense).where(ProjectExpense.id == expense_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ============================================================
    # LABOR
    # ============================================================

    async def add_labor(self, project_id: UUID, labor_data: Dict[str, Any]) -> ProjectLabor:
        labor = ProjectLabor(project_id=project_id, **labor_data)
        self.db.add(labor)
        await self.db.flush()
        await self.db.refresh(labor)
        return labor

    async def get_labor_items(self, project_id: UUID) -> List[ProjectLabor]:
        stmt = select(ProjectLabor).where(
            ProjectLabor.project_id == project_id
        ).order_by(desc(ProjectLabor.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_labor(self, labor_id: UUID) -> bool:
        result = await self.db.execute(
            delete(ProjectLabor).where(ProjectLabor.id == labor_id)
        )
        await self.db.flush()
        return result.rowcount > 0

    # ============================================================
    # STAGES
    # ============================================================

    async def get_stages(self) -> List[ProjectStage]:
        stmt = select(ProjectStage).order_by(ProjectStage.sort_order)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(self) -> dict:
        total_stmt = select(func.count()).select_from(Project)
        total = await self.db.scalar(total_stmt) or 0

        status_stmt = select(
            Project.status,
            func.count().label('count')
        ).group_by(Project.status)
        result = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in result.all()}

        priority_stmt = select(
            Project.priority,
            func.count().label('count')
        ).group_by(Project.priority)
        result = await self.db.execute(priority_stmt)
        priority_counts = {row.priority: row.count for row in result.all()}

        financial_stmt = select(
            func.sum(Project.estimated_cost).label('estimated_total'),
            func.sum(Project.actual_cost).label('actual_total'),
            func.sum(Project.estimated_revenue).label('estimated_revenue'),
            func.sum(Project.actual_revenue).label('actual_revenue'),
        )
        result = await self.db.execute(financial_stmt)
        financial = result.first()

        active_stmt = select(Project).where(
            Project.status == ProjectStatus.ACTIVE
        ).order_by(desc(Project.created_at)).limit(5)
        result = await self.db.execute(active_stmt)
        active_projects = result.scalars().all()

        return {
            "total": total,
            "by_status": status_counts,
            "by_priority": priority_counts,
            "financial": {
                "estimated_total": float(financial.estimated_total or 0),
                "actual_total": float(financial.actual_total or 0),
                "estimated_revenue": float(financial.estimated_revenue or 0),
                "actual_revenue": float(financial.actual_revenue or 0),
            },
            "active_projects": active_projects
        }