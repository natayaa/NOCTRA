# services/projects.py
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from models.projects import Project, ProjectTask, ProjectExpense, ProjectLabor, ProjectActivity
from models.inventory import ProjectWorkshopTask, InventoryMaterialUsage
from models.customer_inquiry import CustomerInquiry
from models.price_list import PriceListItem
from repositories.projects import ProjectRepository
from repositories.customer_inquiry import InquiryRepo
from schemas.constants import InquiryStatus, ProjectStatus, ProjectPriority
from schemas.projects import ProjectCreate, ProjectUpdate


class ProjectService:
    """Service layer for Project management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)

    # ----------------------------------------------------------------------
    # CRUD Operations
    # ----------------------------------------------------------------------

    async def create(self, data: ProjectCreate) -> Project:
        """Create a new project from inquiry."""
        project_data = data.model_dump(exclude_unset=True)
        
        # If inquiry_id is provided, get customer data from inquiry
        if data.inquiry_id:
            inquiry_repo = InquiryRepo(self.db)
            inquiry = await inquiry_repo.get(data.inquiry_id)
            if inquiry:
                project_data.update({
                    "customer_name": inquiry.customer_name or project_data.get("customer_name"),
                    "customer_phone": inquiry.customer_phone_number,
                    "customer_email": inquiry.customer_email,
                    "vehicle_brand": inquiry.vehicle_brand or project_data.get("vehicle_brand"),
                    "vehicle_model": inquiry.vehicle_model or project_data.get("vehicle_model"),
                    "vehicle_year": inquiry.vehicle_year,
                    "vehicle_license_plate": inquiry.vehicle_license_plate,
                })

        # Set default priority if not provided
        if not project_data.get("priority"):
            project_data["priority"] = ProjectPriority.MEDIUM

        project = Project(**project_data)
        self.db.add(project)
        await self.db.flush()

        # Auto-create WorkshopJob
        job = ProjectWorkshopTask(
            project_id=project.id,
            unit_name=project.name,
            status="active",
            estimated_cost=project.estimated_cost or Decimal(0)
        )
        self.db.add(job)
        await self.db.flush()

        # Add activity
        await self.repo.add_activity(
            project.id,
            f"Project created: {project.name}",
            "creation",
            performed_by="system"
        )

        # Update inquiry if linked
        if data.inquiry_id:
            inquiry_repo = InquiryRepo(self.db)
            inquiry = await inquiry_repo.get(data.inquiry_id)
            if inquiry and inquiry.status != InquiryStatus.CONVERTED:
                inquiry.status = InquiryStatus.CONVERTED
                inquiry.converted_at = datetime.now()
                await inquiry_repo.add_activity(
                    data.inquiry_id,
                    f"Converted to project: {project.name}",
                    "conversion",
                    performed_by="system"
                )

        await self.db.flush()
        await self.db.refresh(project)
        return project

    # services/projects.py
    async def get(self, project_id: UUID) -> Project | None:
        """Get a single project by ID (eager loaded)."""
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
        """Get a single project without eager loading."""
        return await self.repo.get_basic(project_id)

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
        """List all projects with filters."""
        return await self.repo.list_all(
            status=status,
            priority=priority,
            brand=brand,
            search=search,
            is_archived=is_archived,
            limit=limit,
            offset=offset
        )

    async def update(self, project_id: UUID, data: ProjectUpdate) -> Project | None:
        """Update a project."""
        update_data = data.model_dump(exclude_unset=True)
        project = await self.repo.update(project_id, update_data)
        if project:
            await self.repo.add_activity(
                project_id,
                "Project updated",
                "update",
                performed_by="system"
            )
            await self.db.flush()
        return project

    async def delete(self, project_id: UUID) -> bool:
        """Delete a project by ID."""
        return await self.repo.delete(project_id)

    async def archive(self, project_id: UUID) -> bool:
        """Archive a project."""
        result = await self.repo.archive(project_id)
        if result:
            await self.repo.add_activity(
                project_id,
                "Project archived",
                "archive",
                performed_by="system"
            )
        return result

    # ----------------------------------------------------------------------
    # Status & Progress
    # ----------------------------------------------------------------------

    async def update_status(
        self,
        project_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Project | None:
        """Update project status."""
        valid_statuses = [e.value for e in ProjectStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        project = await self.repo.update_status(project_id, status, note)
        if project:
            await self.repo.add_activity(
                project_id,
                f"Status updated to {status}" + (f" - {note}" if note else ""),
                "status_change",
                performed_by="system"
            )
            await self.db.flush()
        return project

    async def update_progress(self, project_id: UUID, progress: int) -> Project | None:
        """Update project progress."""
        if progress < 0 or progress > 100:
            raise ValueError("Progress must be between 0 and 100")
        
        project = await self.repo.update_progress(project_id, progress)
        if project:
            await self.repo.add_activity(
                project_id,
                f"Progress updated to {progress}%",
                "progress_update",
                performed_by="system"
            )
            await self.db.flush()
        return project

    async def complete_project(self, project_id: UUID) -> Project | None:
        """Mark a project as completed."""
        project = await self.repo.update_status(
            project_id,
            ProjectStatus.COMPLETED,
            "Project completed"
        )
        if project:
            # Calculate and set actual cost from financials
            financials = await self.get_project_financials(project_id)
            if financials:
                project.actual_cost = financials["actual_cost"]
                project.actual_revenue = financials["actual_revenue"]

            project.progress = 100
            project.completed_at = datetime.now()
            project.actual_delivery_date = datetime.now()

            await self.repo.add_activity(
                project_id,
                "Project completed",
                "completion",
                performed_by="system"
            )

            # Update linked inquiry if any
            if project.inquiry_id:
                inquiry_repo = InquiryRepo(self.db)
                inquiry = await inquiry_repo.get(project.inquiry_id)
                if inquiry and inquiry.status != InquiryStatus.COMPLETED:
                    inquiry.status = InquiryStatus.COMPLETED
                    await inquiry_repo.add_activity(
                        project.inquiry_id,
                        f"Project completed: {project.name}",
                        "completion",
                        performed_by="system"
                    )

            await self.db.flush()
            await self.db.refresh(project)
        return project

    # ----------------------------------------------------------------------
    # Financial Calculations
    # ----------------------------------------------------------------------
    async def get_project_financials(self, project_id: UUID) -> dict | None:
        """Calculate project financials including actual cost."""
        project = await self.repo.get(project_id)
        if not project:
            return None

        # Calculate material cost from usages
        material_cost = Decimal(0)
        material_usages = []
        if project.workshop_job:
            for usage in project.workshop_job.material_usages:
                if usage.item:
                    unit_cost = usage.item.cost_price or Decimal(0)
                    total = usage.quantity * unit_cost
                    material_cost += total
                    material_usages.append({
                        "item_name": usage.item.name,
                        "quantity": float(usage.quantity),
                        "unit": usage.item.unit,
                        "unit_cost": float(unit_cost),
                        "total_cost": float(total),
                    })

        # Calculate labor cost
        labor_cost = Decimal(0)
        labor_items = []
        for labor in project.labor_items:
            labor_cost += labor.total_cost
            labor_items.append({
                "id": str(labor.id),
                "type": labor.labor_type,
                "hours": float(labor.hours),
                "rate": float(labor.rate_per_hour),
                "total": float(labor.total_cost),
                "technician": labor.technician_name,
                "date_performed": labor.date_performed.isoformat() if labor.date_performed else None,
            })

        # Calculate expenses (dari ProjectExpense)
        expenses_total = Decimal(0)
        for exp in project.project_expenses:  # <-- Ganti dari expenses ke project_expenses
            expenses_total += exp.amount

        # Calculate totals
        actual_cost = material_cost + labor_cost + expenses_total
        actual_revenue = project.actual_revenue or Decimal(0)
        estimated_cost = project.estimated_cost or Decimal(0)
        estimated_revenue = project.estimated_revenue or Decimal(0)

        profit = actual_revenue - actual_cost
        margin = (profit / actual_revenue * 100) if actual_revenue else Decimal(0)

        return {
            "project": project,
            "estimated_cost": estimated_cost,
            "actual_cost": actual_cost,
            "estimated_revenue": estimated_revenue,
            "actual_revenue": actual_revenue,
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "expenses": expenses_total,
            "profit": profit,
            "margin": round(margin, 2),
            "material_usages": material_usages,
            "labor_items": labor_items,
            "project_start_date": project.project_start_date,
            "project_target_delivery": project.project_target_delivery,
            "deposit_amount": project.deposit_amount,
            "deposit_paid": project.deposit_paid,
        }

    # ----------------------------------------------------------------------
    # Tasks Management
    # ----------------------------------------------------------------------

    async def add_task(self, project_id: UUID, task_data: Dict[str, Any]) -> ProjectTask:
        """Add a task to a project."""
        task = await self.repo.add_task(project_id, task_data)
        await self.repo.add_activity(
            project_id,
            f"Task added: {task.title}",
            "task_add",
            performed_by="system"
        )
        await self.db.flush()
        return task

    async def get_tasks(self, project_id: UUID) -> List[ProjectTask]:
        """Get all tasks for a project."""
        return await self.repo.get_tasks(project_id)

    async def update_task(self, task_id: UUID, data: Dict[str, Any]) -> ProjectTask | None:
        """Update a task."""
        task = await self.repo.update_task(task_id, data)
        if task:
            # If task is marked as completed, update completed_at
            if data.get("status") == "completed" and not task.completed_at:
                task.completed_at = datetime.now()
                await self.db.flush()
        return task

    async def delete_task(self, task_id: UUID) -> bool:
        """Delete a task."""
        return await self.repo.delete_task(task_id)

    # ----------------------------------------------------------------------
    # Expenses Management
    # ----------------------------------------------------------------------

    async def add_expense(self, project_id: UUID, expense_data: Dict[str, Any]) -> ProjectExpense:
        """Add an expense to a project."""
        expense = await self.repo.add_expense(project_id, expense_data)
        await self.repo.add_activity(
            project_id,
            f"Expense added: {expense.name} - {expense.amount}",
            "expense_add",
            performed_by="system"
        )
        await self.db.flush()
        return expense

    async def get_expenses(self, project_id: UUID) -> List[ProjectExpense]:
        """Get all expenses for a project."""
        return await self.repo.get_expenses(project_id)

    async def delete_expense(self, expense_id: UUID) -> bool:
        """Delete an expense."""
        return await self.repo.delete_expense(expense_id)

    # ----------------------------------------------------------------------
    # Labor Management
    # ----------------------------------------------------------------------

    async def add_labor(
        self,
        project_id: UUID,
        labor_type: str,
        hours: Decimal,
        rate_per_hour: Optional[Decimal] = None,
        technician_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> ProjectLabor:
        """Add a labor entry to a project."""
        if rate_per_hour is None:
            # Fetch from price list
            stmt = (
                select(PriceListItem)
                .where(
                    PriceListItem.category == "labor",
                    PriceListItem.name.ilike(f"%{labor_type}%"),
                    PriceListItem.is_active == True,
                )
                .order_by(PriceListItem.effective_date.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
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
            total_cost=total_cost,
            technician_name=technician_name,
            description=description,
            date_performed=datetime.now()
        )
        self.db.add(labor)
        await self.db.flush()
        
        await self.repo.add_activity(
            project_id,
            f"Labor added: {labor_type} - {hours}h at Rp {rate_per_hour:,.0f}/h",
            "labor_add",
            performed_by="system"
        )
        await self.db.flush()
        return labor

    async def get_labor_items(self, project_id: UUID) -> List[ProjectLabor]:
        """Get all labor entries for a project."""
        return await self.repo.get_labor_items(project_id)

    async def delete_labor(self, labor_id: UUID) -> bool:
        """Delete a labor entry."""
        return await self.repo.delete_labor(labor_id)

    # ----------------------------------------------------------------------
    # Activities
    # ----------------------------------------------------------------------

    async def get_activities(self, project_id: UUID) -> List[ProjectActivity]:
        """Get all activities for a project."""
        return await self.repo.get_activities(project_id)

    # ----------------------------------------------------------------------
    # Stages
    # ----------------------------------------------------------------------

    async def get_stages(self) -> List[Dict]:
        """Get all project stages."""
        stages = await self.repo.get_stages()
        return [
            {
                "id": str(stage.id),
                "name": stage.name,
                "color": stage.color,
                "sort_order": stage.sort_order,
                "description": stage.description,
                "is_default": stage.is_default,
            }
            for stage in stages
        ]

    # ----------------------------------------------------------------------
    # Dashboard & Analytics
    # ----------------------------------------------------------------------

    async def kanban(self) -> dict[str, list]:
        """Generate a Kanban board from projects grouped by status."""
        projects, _ = await self.repo.list_all(is_archived=False)
        
        board = {
            "draft": [],
            "active": [],
            "in_progress": [],
            "on_hold": [],
            "completed": [],
            "cancelled": [],
        }

        for project in projects:
            status = project.status or "draft"
            if status not in board:
                status = "draft"
            board[status].append(self._serialize_project(project))

        return board

    async def get_statistics(self) -> dict:
        """Get project statistics for dashboard."""
        return await self.repo.get_statistics()

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _serialize_project(self, project: Project) -> dict:
        """Convert Project object to a serializable dict for Kanban."""
        return {
            "id": str(project.id),
            "inquiry_id": str(project.inquiry_id) if project.inquiry_id else None,
            "name": project.name,
            "customer_name": project.customer_name,
            "customer_phone": project.customer_phone,
            "vehicle_brand": project.vehicle_brand,
            "vehicle_model": project.vehicle_model,
            "vehicle_year": project.vehicle_year,
            "vehicle_license_plate": project.vehicle_license_plate,
            "status": project.status,
            "priority": project.priority,
            "progress": project.progress or 0,
            "estimated_cost": float(project.estimated_cost or 0),
            "actual_cost": float(project.actual_cost or 0),
            "estimated_revenue": float(project.estimated_revenue or 0),
            "actual_revenue": float(project.actual_revenue or 0),
            "deposit_amount": float(project.deposit_amount or 0),
            "deposit_paid": project.deposit_paid,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "project_start_date": project.project_start_date.isoformat() if project.project_start_date else None,
            "project_target_delivery": project.project_target_delivery.isoformat() if project.project_target_delivery else None,
            "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        }