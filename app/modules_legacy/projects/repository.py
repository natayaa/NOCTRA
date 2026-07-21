# modules/project/repository.py
"""
Project Repository - REFACTORED

✅ Hanya mengelola Project dan sub-entities (tasks, labor, expenses, etc)
✅ Tidak ada logic payment/invoice di sini
✅ Customer/Vehicle data diambil dari Inquiry via relationship
✅ Soft delete support via is_deleted field
"""

from uuid import UUID
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from decimal import Decimal
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, delete
from sqlalchemy.orm import selectinload, joinedload

from core.base import BaseRepository
from core.constants import ProjectStatus
from .models import (
    Project, ProjectDocument, ProjectTask, ProjectExpense, ProjectLabor,
    ProjectActivity, ProjectStage, ProjectPriceListItem, ProjectTeam, ProjectTimeline
)


class ProjectRepository(BaseRepository[Project]):
    """
    Repository untuk Project - TANPA FLUSH/REFRESH/COMMIT.
    
    ✅ Semua operasi hanya mengubah object, tidak menyimpan ke database.
    ✅ Service yang bertanggung jawab untuk flush/commit.
    ✅ Soft delete support.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=Project)

    # ============================================================
    # READ OPERATIONS
    # ============================================================

    async def get_with_details(self, project_id: UUID) -> Optional[Project]:
        """Get project with all related data (eager loading)."""
        stmt = (
            select(Project)
            .where(
                Project.id == project_id,
                Project.is_deleted == False
            )
            .options(
                selectinload(Project.inquiry),
                selectinload(Project.stage),
                selectinload(Project.tasks),
                selectinload(Project.workshop_job).selectinload(
                    Project.workshop_job.property.mapper.class_.material_usages
                ).selectinload(
                    Project.workshop_job.property.mapper.class_.material_usages.property.mapper.class_.item
                ),
                selectinload(Project.material_usages).selectinload(
                    Project.material_usages.property.mapper.class_.item
                ),
                selectinload(Project.activities),
                selectinload(Project.labor_items),
                selectinload(Project.expenses),
                selectinload(Project.price_list_items).selectinload(
                    ProjectPriceListItem.price_list_item
                ),
                selectinload(Project.timeline),
                selectinload(Project.documents),
                selectinload(Project.team_members),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, project_code: str) -> Optional[Project]:
        """Get project by project code."""
        stmt = select(Project).where(
            Project.project_code == project_code,
            Project.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_inquiry(self, inquiry_id: UUID) -> Optional[Project]:
        """Get project by inquiry ID."""
        stmt = select(Project).where(
            Project.inquiry_id == inquiry_id,
            Project.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: Optional[str] = None, priority: Optional[str] = None,
        brand: Optional[str] = None, search: Optional[str] = None,
        is_archived: bool = False, stage_id: Optional[UUID] = None,
        include_deleted: bool = False, limit: int = 100, offset: int = 0
    ) -> tuple[List[Project], int]:
        """
        List all projects with filters.
        
        Args:
            status: Filter by project status
            priority: Filter by priority
            brand: Filter by vehicle brand
            search: Search by name, customer_name, vehicle_brand, vehicle_model
            is_archived: Filter by archived status
            stage_id: Filter by stage
            include_deleted: Include soft-deleted records
            limit: Items per page
            offset: Pagination offset
        
        Returns:
            Tuple of (projects, total_count)
        """
        stmt = select(Project)
        count_stmt = select(func.count()).select_from(Project)

        filters = [Project.is_archived == is_archived]
        
        if not include_deleted:
            filters.append(Project.is_deleted == False)

        if status:
            filters.append(Project.status == status)
        if priority:
            filters.append(Project.priority == priority)
        if brand:
            filters.append(Project.vehicle_brand == brand)
        if stage_id:
            filters.append(Project.stage_id == stage_id)
        if search:
            filters.append(
                or_(
                    Project.name.ilike(f"%{search}%"),
                    Project.customer_name.ilike(f"%{search}%"),
                    Project.customer_email.ilike(f"%{search}%"),
                    Project.vehicle_brand.ilike(f"%{search}%"),
                    Project.vehicle_model.ilike(f"%{search}%"),
                    Project.vehicle_license_plate.ilike(f"%{search}%"),
                    Project.project_code.ilike(f"%{search}%"),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.options(
            selectinload(Project.inquiry),
            selectinload(Project.stage)
        )
        stmt = stmt.order_by(desc(Project.created_at)).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return projects, total

    async def get_by_customer(self, customer_name: str) -> List[Project]:
        """Get projects by customer name."""
        stmt = (
            select(Project)
            .where(
                Project.customer_name.ilike(f"%{customer_name}%"),
                Project.is_deleted == False
            )
            .order_by(desc(Project.created_at))
            .options(selectinload(Project.inquiry))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_active_projects(self) -> List[Project]:
        """Get all active projects."""
        stmt = (
            select(Project)
            .where(
                Project.status == ProjectStatus.ACTIVE,
                Project.is_deleted == False
            )
            .order_by(desc(Project.created_at))
            .options(
                selectinload(Project.stage),
                selectinload(Project.inquiry)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_overdue_projects(self) -> List[Project]:
        """Get projects that are past their target delivery date."""
        now = datetime.now()
        stmt = (
            select(Project)
            .where(
                Project.project_target_delivery < now,
                Project.status != ProjectStatus.COMPLETED,
                Project.status != ProjectStatus.CANCELLED,
                Project.is_deleted == False
            )
            .order_by(Project.project_target_delivery)
            .options(
                selectinload(Project.stage),
                selectinload(Project.inquiry)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent_projects(self, limit: int = 10) -> List[Project]:
        """Get recent projects."""
        stmt = (
            select(Project)
            .where(Project.is_deleted == False)
            .order_by(desc(Project.created_at))
            .limit(limit)
            .options(
                selectinload(Project.stage),
                selectinload(Project.inquiry)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # UPDATE OPERATIONS
    # ============================================================

    async def update(self, pk: UUID, data: Dict[str, Any]) -> Optional[Project]:
        """
        Update project - TANPA flush.
        
        Args:
            pk: Project ID
            data: Data to update
        
        Returns:
            Updated project or None if not found
        """
        project = await self.get(pk)
        if not project or project.is_deleted:
            return None

        for key, value in data.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)

        project.updated_at = datetime.now()
        return project

    async def update_status(
        self,
        project_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[Project]:
        """Update project status - TANPA flush."""
        project = await self.get(project_id)
        if not project or project.is_deleted:
            return None

        old_status = project.status
        project.status = status
        project.updated_at = datetime.now()

        if status == ProjectStatus.COMPLETED:
            project.completed_at = datetime.now()
        elif status == ProjectStatus.CANCELLED:
            project.cancelled_at = datetime.now()

        if note:
            project.notes = note

        return project

    async def update_progress(self, project_id: UUID, progress: int) -> Optional[Project]:
        """Update project progress - TANPA flush."""
        project = await self.get(project_id)
        if not project or project.is_deleted:
            return None

        project.progress = progress
        project.updated_at = datetime.now()

        if progress == 100 and project.status != ProjectStatus.COMPLETED:
            project.status = ProjectStatus.COMPLETED
            project.completed_at = datetime.now()
        elif progress > 0 and project.status == ProjectStatus.DRAFT:
            project.status = ProjectStatus.ACTIVE

        return project

    async def update_stage(self, project_id: UUID, stage_id: UUID) -> Optional[Project]:
        """Update project stage - TANPA flush."""
        project = await self.get(project_id)
        if not project or project.is_deleted:
            return None

        project.stage_id = stage_id
        project.updated_at = datetime.now()
        return project

    async def update_actual_cost(self, project_id: UUID, amount: Decimal) -> Optional[Project]:
        """Update actual cost - TANPA flush."""
        project = await self.get(project_id)
        if not project or project.is_deleted:
            return None

        project.actual_cost = (project.actual_cost or Decimal(0)) + amount
        project.updated_at = datetime.now()
        return project

    async def update_estimated_cost(self, project_id: UUID, amount: Decimal) -> Optional[Project]:
        """Update estimated cost - TANPA flush."""
        project = await self.get(project_id)
        if not project or project.is_deleted:
            return None

        project.estimated_cost = (project.estimated_cost or Decimal(0)) + amount
        project.updated_at = datetime.now()
        return project

    # ============================================================
    # SOFT DELETE OPERATIONS
    # ============================================================

    async def delete(self, pk: UUID) -> bool:
        """
        Soft delete project - TANPA flush.
        
        Args:
            pk: Project ID
        
        Returns:
            True if deleted, False if not found
        """
        project = await self.get(pk)
        if not project:
            return False

        project.is_deleted = True
        project.deleted_at = datetime.now()
        project.is_archived = True
        project.updated_at = datetime.now()
        return True

    async def hard_delete(self, pk: UUID) -> bool:
        """
        Hard delete project - TANPA flush.
        Warning: This cannot be undone!
        """
        project = await self.get(pk, include_deleted=True)
        if not project:
            return False

        await self.db.delete(project)
        return True

    async def archive(self, project_id: UUID) -> Optional[Project]:
        """Archive a project - TANPA flush."""
        project = await self.get(project_id)
        if not project or project.is_deleted:
            return None

        project.is_archived = True
        project.updated_at = datetime.now()
        return project

    async def unarchive(self, project_id: UUID) -> Optional[Project]:
        """Unarchive a project - TANPA flush."""
        project = await self.get(project_id)
        if not project or project.is_deleted:
            return None

        project.is_archived = False
        project.updated_at = datetime.now()
        return project

    # ============================================================
    # FINANCIAL SUMMARY (Aggregate)
    # ============================================================

    async def get_financial_summary(self) -> dict:
        """Get financial summary for all projects - TANPA flush."""
        total_stmt = select(func.count()).select_from(Project).where(
            Project.is_deleted == False
        )
        total = await self.db.scalar(total_stmt) or 0

        financial_stmt = select(
            func.sum(Project.estimated_cost).label('estimated_cost'),
            func.sum(Project.actual_cost).label('actual_cost'),
        ).where(Project.is_deleted == False)
        result = await self.db.execute(financial_stmt)
        financial = result.first()

        # Negative margin projects (actual_cost > estimated_cost)
        negative_stmt = select(func.count()).where(
            Project.actual_cost > Project.estimated_cost,
            Project.status != ProjectStatus.CANCELLED,
            Project.is_deleted == False
        )
        negative_count = await self.db.scalar(negative_stmt) or 0

        return {
            "total_projects": total,
            "estimated_cost": float(financial.estimated_cost or 0),
            "actual_cost": float(financial.actual_cost or 0),
            "negative_margin_projects": negative_count,
            "profit": float(financial.estimated_cost or 0) - float(financial.actual_cost or 0)
        }

    # ============================================================
    # ACTIVITIES
    # ============================================================

    async def add_activity(
        self,
        project_id: UUID,
        activity: str,
        activity_type: Optional[str] = None,
        performed_by: Optional[str] = None,
        meta_data: Optional[dict] = None
    ) -> ProjectActivity:
        """Add activity - TANPA flush."""
        activity_obj = ProjectActivity(
            project_id=project_id,
            activity=activity,
            activity_type=activity_type,
            performed_by=performed_by or "system",
            meta_data=meta_data
        )
        self.db.add(activity_obj)
        return activity_obj

    async def get_activities(
        self,
        project_id: UUID,
        limit: int = 50
    ) -> List[ProjectActivity]:
        """Get all activities for a project."""
        stmt = (
            select(ProjectActivity)
            .where(
                ProjectActivity.project_id == project_id,
                ProjectActivity.is_deleted == False
            )
            .order_by(desc(ProjectActivity.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # TASKS
    # ============================================================

    async def add_task(self, project_id: UUID, task_data: Dict[str, Any]) -> ProjectTask:
        """Add task - TANPA flush."""
        task = ProjectTask(project_id=project_id, **task_data)
        self.db.add(task)
        return task

    async def get_tasks(
        self,
        project_id: UUID,
        status: Optional[str] = None
    ) -> List[ProjectTask]:
        """Get tasks for a project."""
        filters = [ProjectTask.project_id == project_id]
        if status:
            filters.append(ProjectTask.status == status)
        
        stmt = (
            select(ProjectTask)
            .where(and_(*filters))
            .order_by(ProjectTask.sort_order)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_task(self, task_id: UUID) -> Optional[ProjectTask]:
        """Get a single task."""
        stmt = select(ProjectTask).where(
            ProjectTask.id == task_id,
            ProjectTask.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_task(self, task_id: UUID, data: Dict[str, Any]) -> Optional[ProjectTask]:
        """Update a task - TANPA flush."""
        task = await self.get_task(task_id)
        if not task:
            return None

        old_status = task.status
        for key, value in data.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)

        if old_status != "done" and task.status == "done":
            task.completed_at = datetime.now()

        return task

    async def delete_task(self, task_id: UUID) -> bool:
        """Soft delete a task."""
        task = await self.get_task(task_id)
        if not task:
            return False

        task.is_deleted = True
        task.deleted_at = datetime.now()
        return True

    # ============================================================
    # LABOR
    # ============================================================

    async def add_labor(self, project_id: UUID, labor_data: Dict[str, Any]) -> ProjectLabor:
        """Add labor - TANPA flush."""
        labor = ProjectLabor(project_id=project_id, **labor_data)
        self.db.add(labor)
        return labor

    async def get_labor_items(self, project_id: UUID) -> List[ProjectLabor]:
        """Get all labor items for a project."""
        stmt = (
            select(ProjectLabor)
            .where(
                ProjectLabor.project_id == project_id,
                ProjectLabor.is_deleted == False
            )
            .order_by(desc(ProjectLabor.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_labor_item(self, labor_id: UUID) -> Optional[ProjectLabor]:
        """Get a single labor item."""
        stmt = select(ProjectLabor).where(
            ProjectLabor.id == labor_id,
            ProjectLabor.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_labor(self, labor_id: UUID) -> bool:
        """Soft delete a labor item."""
        labor = await self.get_labor_item(labor_id)
        if not labor:
            return False

        labor.is_deleted = True
        labor.deleted_at = datetime.now()
        return True

    # ============================================================
    # EXPENSES
    # ============================================================

    async def add_expense(self, project_id: UUID, expense_data: Dict[str, Any]) -> ProjectExpense:
        """Add expense - TANPA flush."""
        expense = ProjectExpense(project_id=project_id, **expense_data)
        self.db.add(expense)
        return expense

    async def get_expenses(
        self,
        project_id: UUID,
        category: Optional[str] = None
    ) -> List[ProjectExpense]:
        """Get all expenses for a project."""
        filters = [
            ProjectExpense.project_id == project_id,
            ProjectExpense.is_deleted == False
        ]
        if category:
            filters.append(ProjectExpense.category == category)

        stmt = (
            select(ProjectExpense)
            .where(and_(*filters))
            .order_by(desc(ProjectExpense.expense_date))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_expense(self, expense_id: UUID) -> Optional[ProjectExpense]:
        """Get a single expense."""
        stmt = select(ProjectExpense).where(
            ProjectExpense.id == expense_id,
            ProjectExpense.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def approve_expense(
        self,
        expense_id: UUID,
        approved_by: str
    ) -> Optional[ProjectExpense]:
        """Approve an expense - TANPA flush."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return None

        expense.approved_by = approved_by
        expense.approved_at = datetime.now()
        return expense

    async def delete_expense(self, expense_id: UUID) -> bool:
        """Soft delete an expense."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return False

        expense.is_deleted = True
        expense.deleted_at = datetime.now()
        return True

    # ============================================================
    # PRICE LIST ITEMS
    # ============================================================

    async def add_price_list_item(
        self,
        project_id: UUID,
        price_list_item_id: UUID,
        quantity: Decimal,
        unit_price: Decimal,
        notes: Optional[str] = None
    ) -> ProjectPriceListItem:
        """Add price list item - TANPA flush."""
        item = ProjectPriceListItem(
            project_id=project_id,
            price_list_item_id=price_list_item_id,
            quantity=quantity,
            unit_price_at_usage=unit_price,
            total_price=quantity * unit_price,
            notes=notes
        )
        self.db.add(item)
        return item

    async def get_price_list_items(self, project_id: UUID) -> List[ProjectPriceListItem]:
        """Get all price list items for a project."""
        stmt = (
            select(ProjectPriceListItem)
            .where(
                ProjectPriceListItem.project_id == project_id,
                ProjectPriceListItem.is_deleted == False
            )
            .options(selectinload(ProjectPriceListItem.price_list_item))
            .order_by(ProjectPriceListItem.created_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_price_list_item(self, item_id: UUID) -> Optional[ProjectPriceListItem]:
        """Get a single price list item."""
        stmt = select(ProjectPriceListItem).where(
            ProjectPriceListItem.id == item_id,
            ProjectPriceListItem.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_price_list_item(self, item_id: UUID) -> bool:
        """Remove price list item from project."""
        item = await self.get_price_list_item(item_id)
        if not item:
            return False

        item.is_deleted = True
        item.deleted_at = datetime.now()
        return True

    # ============================================================
    # STAGES
    # ============================================================

    async def get_stages(self, active_only: bool = True) -> List[ProjectStage]:
        """Get all project stages."""
        stmt = select(ProjectStage).where(ProjectStage.is_deleted == False)
        if active_only:
            stmt = stmt.where(ProjectStage.is_active == True)
        stmt = stmt.order_by(ProjectStage.sort_order)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_stage(self, stage_id: UUID) -> Optional[ProjectStage]:
        """Get a single stage."""
        stmt = select(ProjectStage).where(
            ProjectStage.id == stage_id,
            ProjectStage.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_stage_by_name(self, name: str) -> Optional[ProjectStage]:
        """Get stage by name."""
        stmt = select(ProjectStage).where(
            ProjectStage.name == name,
            ProjectStage.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_stage(self, stage_data: Dict[str, Any]) -> ProjectStage:
        """Create a new project stage - TANPA flush."""
        stage = ProjectStage(**stage_data)
        self.db.add(stage)
        return stage

    async def update_stage(
        self,
        stage_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[ProjectStage]:
        """Update a stage - TANPA flush."""
        stage = await self.get_stage(stage_id)
        if not stage:
            return None

        for key, value in data.items():
            if hasattr(stage, key) and value is not None:
                setattr(stage, key, value)

        return stage

    async def delete_stage(self, stage_id: UUID) -> bool:
        """Soft delete a stage."""
        stage = await self.get_stage(stage_id)
        if not stage:
            return False

        # Check if stage is used by projects
        stmt = select(func.count()).select_from(Project).where(
            Project.stage_id == stage_id,
            Project.is_deleted == False
        )
        count = await self.db.scalar(stmt) or 0
        if count > 0:
            raise ValueError(f"Cannot delete stage with {count} active projects")

        stage.is_deleted = True
        stage.deleted_at = datetime.now()
        return True

    # ============================================================
    # TIMELINE
    # ============================================================

    async def get_timelines(self, project_id: UUID) -> List[ProjectTimeline]:
        """Get all timelines for a project."""
        stmt = (
            select(ProjectTimeline)
            .where(
                ProjectTimeline.project_id == project_id,
                ProjectTimeline.is_deleted == False
            )
            .order_by(ProjectTimeline.sort_order, ProjectTimeline.due_date)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_timeline(self, timeline_id: UUID) -> Optional[ProjectTimeline]:
        """Get timeline by ID."""
        stmt = select(ProjectTimeline).where(
            ProjectTimeline.id == timeline_id,
            ProjectTimeline.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_timeline(
        self,
        project_id: UUID,
        data: Dict[str, Any]
    ) -> ProjectTimeline:
        """Add timeline - TANPA flush."""
        timeline = ProjectTimeline(project_id=project_id, **data)
        self.db.add(timeline)
        return timeline

    async def update_timeline(
        self,
        timeline_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[ProjectTimeline]:
        """Update timeline - TANPA flush."""
        timeline = await self.get_timeline(timeline_id)
        if not timeline:
            return None

        for key, value in data.items():
            if hasattr(timeline, key) and value is not None:
                setattr(timeline, key, value)

        return timeline

    async def delete_timeline(self, timeline_id: UUID) -> bool:
        """Soft delete timeline."""
        timeline = await self.get_timeline(timeline_id)
        if not timeline:
            return False

        timeline.is_deleted = True
        timeline.deleted_at = datetime.now()
        return True

    # ============================================================
    # DOCUMENTS
    # ============================================================

    async def get_documents(self, project_id: UUID) -> List[ProjectDocument]:
        """Get all documents for a project."""
        stmt = (
            select(ProjectDocument)
            .where(
                ProjectDocument.project_id == project_id,
                ProjectDocument.is_deleted == False
            )
            .order_by(desc(ProjectDocument.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_document(self, document_id: UUID) -> Optional[ProjectDocument]:
        """Get document by ID."""
        stmt = select(ProjectDocument).where(
            ProjectDocument.id == document_id,
            ProjectDocument.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_document(
        self,
        project_id: UUID,
        data: Dict[str, Any],
        file_path: str,
        file_name: str
    ) -> ProjectDocument:
        """Add document - TANPA flush."""
        document = ProjectDocument(
            project_id=project_id,
            file_path=file_path,
            file_name=file_name,
            **data
        )
        self.db.add(document)
        return document

    async def update_document(
        self,
        document_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[ProjectDocument]:
        """Update document metadata - TANPA flush."""
        document = await self.get_document(document_id)
        if not document:
            return None

        for key, value in data.items():
            if hasattr(document, key) and value is not None:
                setattr(document, key, value)

        return document

    async def delete_document(self, document_id: UUID) -> bool:
        """Soft delete document."""
        document = await self.get_document(document_id)
        if not document:
            return False

        document.is_deleted = True
        document.deleted_at = datetime.now()
        return True

    # ============================================================
    # TEAM
    # ============================================================

    async def get_team_members(self, project_id: UUID) -> List[ProjectTeam]:
        """Get all team members for a project."""
        stmt = (
            select(ProjectTeam)
            .where(
                ProjectTeam.project_id == project_id,
                ProjectTeam.is_deleted == False
            )
            .order_by(ProjectTeam.assigned_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_team_member(
        self,
        project_id: UUID,
        user_id: UUID
    ) -> Optional[ProjectTeam]:
        """Get team member by project and user."""
        stmt = select(ProjectTeam).where(
            ProjectTeam.project_id == project_id,
            ProjectTeam.user_id == user_id,
            ProjectTeam.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_team_member(
        self,
        project_id: UUID,
        data: Dict[str, Any]
    ) -> ProjectTeam:
        """Add team member - TANPA flush."""
        team_member = ProjectTeam(project_id=project_id, **data)
        self.db.add(team_member)
        return team_member

    async def remove_team_member(self, team_member_id: UUID) -> bool:
        """Remove team member."""
        team_member = await self.get_team_member_by_id(team_member_id)
        if not team_member:
            return False

        team_member.is_deleted = True
        team_member.deleted_at = datetime.now()
        return True

    async def get_team_member_by_id(self, team_member_id: UUID) -> Optional[ProjectTeam]:
        """Get team member by ID."""
        stmt = select(ProjectTeam).where(
            ProjectTeam.id == team_member_id,
            ProjectTeam.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_team_member_role(
        self,
        team_member_id: UUID,
        role: str
    ) -> Optional[ProjectTeam]:
        """Update team member role - TANPA flush."""
        team_member = await self.get_team_member_by_id(team_member_id)
        if not team_member:
            return None

        team_member.role = role
        return team_member

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(self) -> dict:
        """Get project statistics for dashboard."""
        # Total projects
        total_stmt = select(func.count()).select_from(Project).where(
            Project.is_deleted == False
        )
        total = await self.db.scalar(total_stmt) or 0

        # By status
        status_stmt = (
            select(Project.status, func.count().label("count"))
            .where(Project.is_deleted == False)
            .group_by(Project.status)
        )
        result_status = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in result_status.all()}

        # By priority
        priority_stmt = (
            select(Project.priority, func.count().label("count"))
            .where(Project.is_deleted == False)
            .group_by(Project.priority)
        )
        result_priority = await self.db.execute(priority_stmt)
        priority_counts = {row.priority: row.count for row in result_priority.all()}

        # Financial summary
        financial_stmt = (
            select(
                func.sum(Project.estimated_cost).label("estimated_total"),
                func.sum(Project.actual_cost).label("actual_total"),
            )
            .where(
                Project.is_archived == False,
                Project.is_deleted == False
            )
        )
        result_finance = await self.db.execute(financial_stmt)
        financial = result_finance.first()

        # Active projects (top 5)
        active_stmt = (
            select(Project)
            .where(
                Project.status == ProjectStatus.ACTIVE,
                Project.is_deleted == False
            )
            .order_by(desc(Project.created_at))
            .limit(5)
            .options(
                selectinload(Project.stage),
                selectinload(Project.inquiry)
            )
        )
        result_active = await self.db.execute(active_stmt)
        active_projects = result_active.scalars().all()

        active_projects_data = []
        for project in active_projects:
            active_projects_data.append({
                "id": str(project.id),
                "name": project.name,
                "project_code": project.project_code,
                "customer_name": project.customer_name,
                "vehicle_brand": project.vehicle_brand,
                "vehicle_model": project.vehicle_model,
                "status": project.status,
                "priority": project.priority,
                "progress": project.progress or 0,
                "estimated_cost": float(project.estimated_cost or 0),
                "actual_cost": float(project.actual_cost or 0),
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "stage": {
                    "id": str(project.stage.id),
                    "name": project.stage.name,
                    "color": project.stage.color
                } if project.stage else None
            })

        return {
            "total": total,
            "by_status": status_counts,
            "by_priority": priority_counts,
            "financial": {
                "estimated_total": float(financial.estimated_total or 0),
                "actual_total": float(financial.actual_total or 0),
                "profit": float(financial.estimated_total or 0) - float(financial.actual_total or 0),
            },
            "active_projects": active_projects_data
        }