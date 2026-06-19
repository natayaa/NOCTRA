from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.projects import Project, ProjectLabor, ProjectExpense
from models.inventory_workshop_jobs import WorkshopJob
from models.inventory_material_usage import JobMaterialUsage
from models.price_list import PriceListItem
from repositories.projects import ProjectRepository
from repositories.customer_inquiry import InquiryRepo
from schemas.constants import InquiryStatus


class ProjectService:
    """Service layer for Project management."""

    def __init__(self) -> None:
        self.repo = ProjectRepository()

    # ----------------------------------------------------------------------
    # CRUD Operations
    # ----------------------------------------------------------------------

    async def create(self, db: AsyncSession, payload: dict) -> Project:
        """Create a new project and auto-create its WorkshopJob."""
        project = Project(**payload)
        db.add(project)
        await db.flush()

        # Auto-create WorkshopJob for this project
        job = WorkshopJob(
            project_id=project.id,
            unit_name=project.name,
            status="active",
            estimated_cost=project.estimated_cost or Decimal(0)
        )
        db.add(job)
        await db.flush()

        return project

    async def get(self, db: AsyncSession, project_id: str) -> Project | None:
        """Get a single project by ID (eager loaded)."""
        return await self.repo.get(db, project_id)

    async def list_all(self, db: AsyncSession) -> list[Project]:
        """List all projects."""
        return await self.repo.list(db)

    async def delete(self, db: AsyncSession, project_id: str) -> bool:
        """Delete a project by ID."""
        return await self.repo.delete(db, project_id)

    # ----------------------------------------------------------------------
    # Financial Calculations
    # ----------------------------------------------------------------------

    async def get_project_financials(self, db: AsyncSession, project_id: str) -> dict | None:
        """
        Calculate detailed financial summary for a project.

        Returns:
            dict with keys: estimated_cost, actual_cost, estimated_revenue,
            actual_revenue, material_cost, labor_cost, expenses, profit, margin.
        """
        project = await self.repo.get(db, project_id)
        if not project:
            return None

        # Material cost from workshop_job
        material_cost = Decimal(0)
        if project.workshop_job:
            for usage in project.workshop_job.material_usages:
                if usage.item:
                    material_cost += usage.quantity * usage.item.cost_price

        # Labor cost from ProjectLabor
        labor_cost = Decimal(0)
        for labor in project.labor_items:
            labor_cost += labor.total_cost

        # Additional expenses
        expenses = Decimal(0)
        for exp in project.expenses:
            expenses += exp.amount

        actual_cost = material_cost + labor_cost + expenses

        # Revenue values
        actual_revenue = project.actual_revenue or Decimal(0)
        estimated_revenue = project.estimated_revenue or Decimal(0)

        profit = actual_revenue - actual_cost
        margin = (profit / actual_revenue * 100) if actual_revenue else Decimal(0)

        return {
            "estimated_cost": project.estimated_cost or Decimal(0),
            "actual_cost": actual_cost,
            "estimated_revenue": estimated_revenue,
            "actual_revenue": actual_revenue,
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "expenses": expenses,
            "profit": profit,
            "margin": round(margin, 2),
        }

    # ----------------------------------------------------------------------
    # Project Actions
    # ----------------------------------------------------------------------

    async def complete_project(self, db: AsyncSession, project_id: str) -> Project | None:
        """
        Mark a project as completed.
        - Sets status to 'completed', progress to 100, completed_at = now.
        - Updates actual_cost from financials.
        - If linked to an inquiry, updates inquiry status to 'completed'.
        """
        project = await self.repo.get(db, project_id)
        if not project:
            return None

        # Calculate and set actual cost from financials
        financials = await self.get_project_financials(db, project_id)
        if financials:
            project.actual_cost = financials["actual_cost"]

        project.status = "completed"
        project.progress = 100
        project.completed_at = datetime.now()

        # Update linked inquiry if any
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

    # ----------------------------------------------------------------------
    # Labor Management
    # ----------------------------------------------------------------------

    async def add_labor(
        self,
        db: AsyncSession,
        project_id: str,
        labor_type: str,
        hours: Decimal,
        rate_per_hour: Decimal | None = None
    ) -> ProjectLabor:
        """
        Add a labor entry to a project.
        If rate_per_hour is not provided, it's fetched from the price list.
        """
        if rate_per_hour is None:
            stmt = (
                select(PriceListItem)
                .where(
                    PriceListItem.category == "labor",
                    PriceListItem.name == labor_type,
                    PriceListItem.is_active == True,
                )
                .order_by(PriceListItem.effective_date.desc())
                .limit(1)
            )
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
            total_cost=total_cost,
        )
        db.add(labor)
        await db.flush()
        return labor

    async def get_labor_list(self, db: AsyncSession, project_id: str) -> list[ProjectLabor]:
        """Get all labor entries for a project."""
        project = await self.repo.get(db, project_id)
        return project.labor_items if project else []

    async def delete_labor(self, db: AsyncSession, labor_id: str) -> bool:
        """Delete a labor entry by ID."""
        labor = await db.get(ProjectLabor, labor_id)
        if not labor:
            return False
        await db.delete(labor)
        await db.flush()
        return True

    # ----------------------------------------------------------------------
    # Dashboard & Analytics Helpers
    # ----------------------------------------------------------------------

    async def kanban(self, db: AsyncSession) -> dict[str, list]:
        """Generate a Kanban board from projects grouped by status."""
        result = await db.execute(select(Project))
        projects = result.scalars().all()

        # Define valid statuses (based on project status enum)
        board = {
            "new": [],
            "quoted": [],
            "approved": [],
            "preparation": [],
            "painting": [],
            "assembly": [],
            "completed": [],
        }

        for project in projects:
            status = project.status or "new"
            if status not in board:
                status = "new"  # fallback
            board[status].append(self._serialize_project(project))

        return board

    async def revenue_summary(self, db: AsyncSession) -> dict:
        """Calculate total revenue, cost, and profit across all projects."""
        result = await db.execute(
            select(
                func.sum(Project.actual_revenue),
                func.sum(Project.actual_cost)
            )
        )
        revenue, cost = result.one()
        total_revenue = Decimal(str(revenue or 0))
        total_cost = Decimal(str(cost or 0))
        return {
            "total_revenue": float(total_revenue),
            "total_cost": float(total_cost),
            "profit": float(total_revenue - total_cost),
        }

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _serialize_project(self, project: Project) -> dict:
        """Convert Project object to a serializable dict for Kanban."""
        return {
            "id": project.id,
            "inquiry_id": project.inquiry_id,
            "name": project.name,
            "customer_name": project.customer_name,
            "vehicle_brand": project.vehicle_brand,
            "vehicle_model": project.vehicle_model,
            "status": project.status,
            "progress": project.progress or 0,
            "estimated_cost": float(project.estimated_cost or 0),
            "actual_cost": float(project.actual_cost or 0),
            "estimated_revenue": float(project.estimated_revenue or 0),
            "actual_revenue": float(project.actual_revenue or 0),
        }