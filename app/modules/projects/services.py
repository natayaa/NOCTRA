# modules/project/services.py
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.exceptions import NotFoundError, ValidationError, BusinessError
from core.constants import InquiryStatus, ProjectStatus, ProjectPriority
from .models import (
    Project, ProjectDocument, ProjectTask, ProjectLabor, ProjectActivity,
    ProjectExpense, ProjectStage, ProjectPriceListItem, ProjectTimeline, ProjectTeam
)
from .repository import ProjectRepository
from .schemas import (
    ProjectCreate, ProjectDocumentCreate, ProjectDocumentUpdate,
    ProjectDocumentUpload, ProjectTimelineCreate, ProjectTimelineUpdate,
    ProjectUpdate, ProjectTaskCreate, ProjectTeamCreate, ProjectLaborCreate,
    ProjectExpenseCreate, ProjectStageCreate
)

from modules.inquiry.repository import InquiryRepository
from modules.inventory.models import ProjectWorkshopTask
from modules.price_list.models import PriceListItem
from modules.price_list.repository import PriceListRepository
from modules.payment.repository import PaymentRepository


class ProjectService:
    """Service untuk project management - HANDLE TRANSACTION."""
    # Field yang TIDAK ADA di model Project
    EXCLUDED_FIELDS = {'price_list_item_ids'}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.price_list_repo = PriceListRepository(db)

    # ==================== CRUD ====================

    async def create(self, data: ProjectCreate) -> Project:
        """Create a new project - handle transaction."""
        try:
            # 1. Prepare project data (exclude fields not in model)
            project_data = data.model_dump(
                exclude_unset=True,
                exclude=self.EXCLUDED_FIELDS
            )

            # Set default priority if not provided
            if not project_data.get("priority"):
                project_data['priority'] = ProjectPriority.MEDIUM

            # 2. Get inquiry if linked
            inquiry = None
            if data.inquiry_id:
                inquiry_repo = InquiryRepository(self.db)
                inquiry = await inquiry_repo.get(data.inquiry_id)
                if inquiry:
                    project_data.update({
                        "customer_name": inquiry.customer_name or project_data.get("customer_name"),
                        "customer_phone": inquiry.customer_phone_number,
                        "customer_email": inquiry.customer_email,
                        "vehicle_brand": inquiry.vehicle_brand or project_data.get("vehicle_brand"),
                        "vehicle_model": inquiry.vehicle_model or project_data.get("vehicle_model"),
                        "vehicle_year": inquiry.vehicle_year,
                        "vehicle_license_plate": inquiry.vehicle_license_plate
                    })

            # 3. Calculate estimated cost from price list items
            price_list_ids = data.price_list_item_ids or []
            if price_list_ids:
                estimated_cost = Decimal(0)
                for item_id in price_list_ids:
                    price_item = await self.price_list_repo.get(item_id)
                    if price_item:
                        estimated_cost += price_item.price
                    else:
                        raise ValidationError(
                            f"Price list item '{item_id}' not found")
                project_data["estimated_cost"] = estimated_cost

            # 4. Create project
            project = Project(**project_data)
            self.db.add(project)

            # Flush to get project ID
            await self.db.flush()

            # 5. Add price list items to junction table
            if price_list_ids:
                for item_id in price_list_ids:
                    price_item = await self.price_list_repo.get(item_id)
                    if price_item:
                        project_price_item = ProjectPriceListItem(
                            project_id=project.id,
                            price_list_item_id=item_id,
                            quantity=Decimal(1),
                            unit_price_at_usage=price_item.price,
                            total_price=price_item.price
                        )
                        self.db.add(project_price_item)

            # 6. Auto create workshop job
            job = ProjectWorkshopTask(
                project_id=project.id,
                unit_name=project.name,
                status="pending",
                estimated_cost=project.estimated_cost or Decimal(0)
            )
            self.db.add(job)

            # 7. Add activity
            await self.repo.add_activity(
                project.id,
                f"Project created: {project.name}",
                "creation",
                performed_by="system"
            )

            # 8. Update inquiry if linked
            if data.inquiry_id and inquiry:
                if inquiry.status != InquiryStatus.CONVERTED:
                    inquiry.status = InquiryStatus.CONVERTED
                    inquiry.converted_at = datetime.now()

            # 9. Commit all changes
            await self.db.flush()
            await self.db.refresh(project)
            await self.db.commit()

            return project

        except ValidationError as e:
            await self.db.rollback()
            raise e
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID."""
        return await self.repo.get_with_details(project_id)

    async def list_all(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        brand: Optional[str] = None,
        search: Optional[str] = None,
        is_archived: bool = False,
        stage_id: Optional[UUID] = None,
        limit: int = 10,
        offset: int = 0
    ) -> tuple[List[Project], int]:
        """List all projects with filters."""
        return await self.repo.list_all(
            status=status,
            priority=priority,
            brand=brand,
            search=search,
            is_archived=is_archived,
            stage_id=stage_id,
            limit=limit,
            offset=offset
        )

    async def update(self, project_id: UUID, data: ProjectUpdate) -> Optional[Project]:
        """Update a project - handle transaction."""
        try:
            update_data = data.model_dump(
                exclude_unset=True, exclude=self.EXCLUDED_FIELDS)
            project = await self.repo.update(project_id, **update_data)

            if project:
                await self.repo.add_activity(
                    project_id,
                    "Project updated",
                    "update",
                    performed_by="system"
                )
                await self.db.flush()
                await self.db.refresh(project)
                await self.db.commit()

            return project

        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete(self, project_id: UUID) -> bool:
        """Delete a project - handle transaction."""
        try:
            result = await self.repo.delete(project_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e

    async def archive(self, project_id: UUID) -> bool:
        """Archive a project - handle transaction."""
        try:
            project = await self.repo.archive(project_id)
            if project:
                await self.repo.add_activity(
                    project_id,
                    "Project archived",
                    "archive",
                    performed_by="system"
                )
                await self.db.flush()
                await self.db.refresh(project)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            await self.db.rollback()
            raise e

    async def unarchive(self, project_id: UUID) -> bool:
        """Unarchive a project - handle transaction."""
        try:
            project = await self.repo.unarchive(project_id)
            if project:
                await self.repo.add_activity(
                    project_id,
                    "Project unarchived",
                    "unarchive",
                    performed_by="system"
                )
                await self.db.flush()
                await self.db.refresh(project)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== STATUS & PROGRESS ====================

    async def update_status(self, project_id: UUID, status: str, note: Optional[str] = None) -> Optional[Project]:
        """Update project status - handle transaction."""
        try:
            valid_statuses = [e.value for e in ProjectStatus]
            if status not in valid_statuses:
                raise ValidationError(f"Invalid project status: {status}")

            project = await self.repo.update_status(project_id, status, note)

            if project:
                # Add status change activity
                await self.repo.add_activity(
                    project_id,
                    f"Status changed to {status}",
                    "status_change",
                    performed_by="system",
                    meta_data={"new_status": status, "note": note}
                )
                await self.db.flush()
                await self.db.refresh(project)
                await self.db.commit()

            return project

        except Exception as e:
            await self.db.rollback()
            raise e

    async def update_progress(self, project_id: UUID, progress: int) -> Optional[Project]:
        """Update project progress - handle transaction."""
        try:
            if progress < 0 or progress > 100:
                raise ValidationError("Progress must be between 0 and 100")

            project = await self.repo.update_progress(project_id, progress)

            if project:
                await self.repo.add_activity(
                    project_id,
                    f"Progress updated to {progress}%",
                    "progress_update",
                    performed_by="system"
                )
                await self.db.flush()
                await self.db.refresh(project)
                await self.db.commit()

            return project

        except Exception as e:
            await self.db.rollback()
            raise e

    async def complete_project(self, project_id: UUID) -> Optional[Project]:
        """Complete a project - handle transaction."""
        try:
            project = await self.repo.get_with_details(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            # Calculate actual cost
            financials = await self.get_project_financials(project_id)
            if financials:
                project.actual_cost = Decimal(str(financials['actual_cost']))

            project.status = ProjectStatus.COMPLETED
            project.progress = 100
            project.completed_at = datetime.now()
            project.actual_delivery_date = datetime.now()

            await self.repo.add_activity(
                project_id,
                "Project Completed",
                "completion",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(project)
            await self.db.commit()

            return project

        except Exception as e:
            await self.db.rollback()
            raise e

    async def cancel_project(self, project_id: UUID, reason: str) -> Optional[Project]:
        """Cancel a project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            if project.status in [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]:
                raise BusinessError(
                    f"Cannot cancel project with status: {project.status}")

            project.status = ProjectStatus.CANCELLED
            project.cancelled_at = datetime.now()
            project.cancellation_reason = reason

            await self.repo.add_activity(
                project_id,
                f"Project cancelled: {reason}",
                "cancellation",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(project)
            await self.db.commit()

            return project

        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== FINANCIAL ====================

    async def get_project_financials(self, project_id: UUID) -> Dict:
        """Get detailed financial breakdown for a project."""
        project = await self.repo.get_with_details(project_id)
        if not project:
            raise NotFoundError(f"Project {project_id} not found")

        material_cost = Decimal(0)
        material_usages = []

        if project.workshop_job:
            for usage in project.workshop_job.material_usages:
                if usage.item:
                    unit_cost = usage.unit_cost or Decimal(0)
                    total = usage.quantity * unit_cost
                    material_cost += total
                    material_usages.append({
                        "id": str(usage.id),
                        "item_name": usage.item.name,
                        "quantity": float(usage.quantity),
                        "unit": usage.item.unit,
                        "unit_cost": float(unit_cost),
                        "total_cost": float(total),
                        "is_waste": usage.is_waste
                    })

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
                "technician": labor.technical_name,
                "date_performed": labor.date_performed.isoformat() if labor.date_performed else None
            })

        expenses_total = Decimal(0)
        for exp in project.expenses:
            expenses_total += exp.amount

        actual_cost = material_cost + labor_cost + expenses_total
        actual_revenue = project.actual_revenue or Decimal(0)
        estimated_cost = project.estimated_cost or Decimal(0)
        estimated_revenue = project.estimated_revenue or Decimal(0)
        profit = actual_revenue - actual_cost
        margin = (profit / actual_revenue *
                  100) if actual_revenue else Decimal(0)

        total_paid = Decimal(0)
        deposit_paid = Decimal(0)
        if project.inquiry:
            deposit_paid = project.inquiry.deposit_paid or Decimal(0)
            total_paid = project.inquiry.total_paid or Decimal(0)

        return {
            "estimated_cost": float(estimated_cost),
            "actual_cost": float(actual_cost),
            "estimated_revenue": float(estimated_revenue),
            "actual_revenue": float(actual_revenue),
            "material_cost": float(material_cost),
            "labor_cost": float(labor_cost),
            "expenses": float(expenses_total),
            "profit": float(profit),
            "margin": float(round(margin, 2)),
            "total_paid": float(total_paid),
            "deposit_paid": float(deposit_paid),
            "remaining_balance": float(actual_cost - total_paid),
            "material_usages": material_usages,
            "labor_items": labor_items
        }

    # ==================== TASKS ====================

    async def add_task(self, project_id: UUID, task_data: Dict[str, Any]) -> ProjectTask:
        """Add a task to project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            task = await self.repo.add_task(project_id, task_data)

            await self.repo.add_activity(
                project_id,
                f"Task added: {task.title}",
                "task_add",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(task)
            await self.db.commit()

            return task

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_tasks(self, project_id: UUID, status: Optional[str] = None) -> List[ProjectTask]:
        """Get all tasks for a project."""
        return await self.repo.get_tasks(project_id, status)

    async def update_task(self, task_id: UUID, data: Dict[str, Any]) -> Optional[ProjectTask]:
        """Update a task - handle transaction."""
        try:
            task = await self.repo.update_task(task_id, data)
            if task:
                await self.db.flush()
                await self.db.refresh(task)
                await self.db.commit()
            return task
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_task(self, task_id: UUID) -> bool:
        """Delete a task - handle transaction."""
        try:
            result = await self.repo.delete_task(task_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e

    async def complete_task(self, task_id: UUID) -> Optional[ProjectTask]:
        """Mark a task as completed - handle transaction."""
        try:
            task = await self.repo.get_task(task_id)
            if not task:
                raise NotFoundError(f"Task {task_id} not found")

            task = await self.repo.update_task(task_id, {
                "status": "completed",
                "completed_at": datetime.now()
            })

            await self.db.flush()
            await self.db.refresh(task)
            await self.db.commit()

            return task

        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== LABOR ====================

    async def add_labor(
        self,
        project_id: UUID,
        labor_type: str,
        hours: Decimal,
        rate_per_hour: Optional[Decimal] = None,
        technician_name: Optional[str] = None,
        description: Optional[str] = None,
        date_performed: Optional[datetime] = None
    ) -> ProjectLabor:
        """Add labor to project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            # Get rate from price list if not provided
            if rate_per_hour is None:
                stmt = (
                    select(PriceListItem)
                    .where(
                        PriceListItem.category == "labor",
                        PriceListItem.name.ilike(f"%{labor_type}%"),
                        PriceListItem.is_active == True
                    )
                    .order_by(PriceListItem.effective_date.desc())
                    .limit(1)
                )
                result = await self.db.execute(stmt)
                price_item = result.scalar_one_or_none()
                if not price_item:
                    raise ValidationError(
                        f"Labor type '{labor_type}' not found in price list. "
                        "Please provide rate_per_hour manually."
                    )
                rate_per_hour = price_item.price

            total_cost = hours * rate_per_hour

            labor = await self.repo.add_labor(project_id, {
                "labor_type": labor_type,
                "hours": hours,
                "rate_per_hour": rate_per_hour,
                "total_cost": total_cost,
                "technical_name": technician_name,
                "description": description,
                "date_performed": date_performed or datetime.now()
            })

            # Update project actual cost
            project.actual_cost += total_cost

            await self.repo.add_activity(
                project_id,
                f"Labor added: {labor_type} - {hours} hours (Rp {total_cost:,.2f})",
                "labor_add",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(labor)
            await self.db.commit()

            return labor

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_labor_items(self, project_id: UUID) -> List[ProjectLabor]:
        """Get all labor items for a project."""
        return await self.repo.get_labor_items(project_id)

    async def delete_labor(self, labor_id: UUID) -> bool:
        """Delete a labor item - handle transaction."""
        try:
            # Get labor first to subtract from project actual cost
            labor = await self.repo.get(labor_id)
            if labor:
                project = await self.repo.get(labor.project_id)
                if project:
                    project.actual_cost -= labor.total_cost

            result = await self.repo.delete_labor(labor_id)
            await self.db.flush()
            await self.db.commit()
            return result

        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== EXPENSES ====================

    async def add_expense(
        self,
        project_id: UUID,
        name: str,
        category: str,
        amount: Decimal,
        description: Optional[str] = None,
        expense_date: Optional[datetime] = None,
        is_billable: bool = True
    ) -> ProjectExpense:
        """Add an expense to project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            expense = await self.repo.add_expense(project_id, {
                "name": name,
                "category": category,
                "amount": amount,
                "description": description,
                "expense_date": expense_date or datetime.now(),
                "is_billable": is_billable
            })

            project.actual_cost += amount

            await self.repo.add_activity(
                project_id,
                f"Expense added: {name} - Rp {amount:,.2f}",
                "expense_add",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(expense)
            await self.db.commit()

            return expense

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_expenses(self, project_id: UUID, category: Optional[str] = None) -> List[ProjectExpense]:
        """Get all expenses for a project."""
        return await self.repo.get_expenses(project_id, category)

    async def approve_expense(self, expense_id: UUID, approved_by: str) -> Optional[ProjectExpense]:
        """Approve an expense - handle transaction."""
        try:
            expense = await self.repo.approve_expense(expense_id, approved_by)
            if expense:
                await self.db.flush()
                await self.db.refresh(expense)
                await self.db.commit()
            return expense
        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== PRICE LIST ITEMS ====================

    async def add_price_list_item(
        self,
        project_id: UUID,
        price_list_item_id: UUID,
        quantity: Decimal = Decimal(1),
        notes: Optional[str] = None
    ) -> ProjectPriceListItem:
        """Add a price list item to project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            price_item = await self.price_list_repo.get(price_list_item_id)
            if not price_item:
                raise NotFoundError(
                    f"Price list item {price_list_item_id} not found")

            if not price_item.is_active:
                raise ValidationError(
                    f"Price list item '{price_item.name}' is not active")

            item = await self.repo.add_price_list_item(
                project_id=project_id,
                price_list_item_id=price_list_item_id,
                quantity=quantity,
                unit_price=price_item.price,
                notes=notes
            )

            project.estimated_cost += item.total_price

            await self.repo.add_activity(
                project_id,
                f"Price list item added: {price_item.name} x {quantity}",
                "price_list_add",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(item)
            await self.db.commit()

            return item

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_price_list_items(self, project_id: UUID) -> List[ProjectPriceListItem]:
        """Get all price list items for a project."""
        return await self.repo.get_price_list_items(project_id)

    async def remove_price_list_item(self, item_id: UUID) -> bool:
        """Remove a price list item from project - handle transaction."""
        try:
            # Get the item first
            stmt = select(ProjectPriceListItem).where(
                ProjectPriceListItem.id == item_id)
            result = await self.db.execute(stmt)
            item = result.scalar_one_or_none()

            if not item:
                return False

            # Update project estimated cost
            project = await self.repo.get(item.project_id)
            if project:
                project.estimated_cost -= item.total_price

            # Delete from junction table
            await self.db.delete(item)

            await self.repo.add_activity(
                item.project_id,
                "Price list item removed",
                "price_list_remove",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.commit()

            return True

        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== STAGES ====================

    async def get_stages(self, active_only: bool = True) -> List[Dict]:
        """Get all project stages."""
        stages = await self.repo.get_stages(active_only)
        return [
            {
                "id": str(stage.id),
                "name": stage.name,
                "color": stage.color,
                "sort_order": stage.sort_order,
                "description": stage.description,
                "is_default": stage.is_default,
                "is_active": stage.is_active
            } for stage in stages
        ]

    async def create_stage(self, data: Dict[str, Any]) -> ProjectStage:
        """Create a new project stage - handle transaction."""
        try:
            existing_stages = await self.repo.get_stages(active_only=False)
            for stage in existing_stages:
                if stage.name.lower() == data.get("name", "").lower():
                    raise ValidationError(
                        f"Stage '{data.get('name')}' already exists")

            stage = await self.repo.create_stage(data)
            await self.db.flush()
            await self.db.refresh(stage)
            await self.db.commit()

            return stage

        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== DASHBOARD ====================

    async def kanban(self) -> Dict[str, List]:
        """Get Kanban board data."""
        projects, _ = await self.repo.list_all(is_archived=False)
        board = {
            "draft": [], "active": [], "in_progress": [],
            "on_hold": [], "completed": [], "cancelled": []
        }

        for project in projects:
            status = project.status or "draft"
            if status not in board:
                status = "draft"
            board[status].append(self._serialize_project(project))

        return board

    async def get_statistics(self) -> Dict:
        """Get project statistics."""
        return await self.repo.get_statistics()

    async def get_financial_summary(self) -> Dict:
        """Get financial summary for all projects."""
        return await self.repo.get_financial_summary()

    # ==================== ACTIVITIES ====================

    async def get_activities(self, project_id: UUID, limit: int = 50) -> List[ProjectActivity]:
        """Get all activities for a project."""
        return await self.repo.get_activities(project_id, limit)

    # ==================== TIMELINE ====================

    async def add_timeline(self, project_id: UUID, data: ProjectTimelineCreate) -> ProjectTimeline:
        """Add timeline to project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            timeline = await self.repo.add_timeline(project_id, data.model_dump())

            await self.repo.add_activity(
                project_id,
                f"Timeline added: {data.milestone_name}",
                "timeline_add",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(timeline)
            await self.db.commit()

            return timeline

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_timelines(self, project_id: UUID) -> List[ProjectTimeline]:
        """Get all timelines for a project."""
        return await self.repo.get_timelines(project_id)

    async def update_timeline(self, timeline_id: UUID, data: ProjectTimelineUpdate) -> Optional[ProjectTimeline]:
        """Update timeline - handle transaction."""
        try:
            timeline = await self.repo.update_timeline(timeline_id, data.model_dump(exclude_unset=True))
            if timeline:
                await self.db.flush()
                await self.db.refresh(timeline)
                await self.db.commit()
            return timeline
        except Exception as e:
            await self.db.rollback()
            raise e

    async def complete_timeline(self, timeline_id: UUID) -> Optional[ProjectTimeline]:
        """Mark timeline as completed - handle transaction."""
        try:
            timeline = await self.repo.update_timeline(timeline_id, {
                "status": "completed",
                "completed_at": datetime.now()
            })
            if timeline:
                await self.db.flush()
                await self.db.refresh(timeline)
                await self.db.commit()
            return timeline
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_timeline(self, timeline_id: UUID) -> bool:
        """Delete timeline - handle transaction."""
        try:
            result = await self.repo.delete_timeline(timeline_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== DOCUMENTS ====================

    async def upload_document(
        self,
        project_id: UUID,
        file: UploadFile,
        data: ProjectDocumentUpload
    ) -> ProjectDocument:
        """Upload document to project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            if not file.filename:
                raise ValidationError("File name is required")

            content = await file.read()
            file_size = len(content)
            if file_size > 10 * 1024 * 1024:
                raise ValidationError("File size exceeds 10MB limit")

            upload_dir = Path("uploads/projects") / str(project_id)
            upload_dir.mkdir(parents=True, exist_ok=True)

            ext = Path(file.filename).suffix
            filename = f"{uuid4()}{ext}"
            file_path = upload_dir / filename

            with open(file_path, "wb") as f:
                f.write(content)

            document_data = {
                "name": data.name,
                "document_type": data.document_type,
                "description": data.description,
                "is_public": data.is_public,
                "file_size": len(content),
                "mime_type": file.content_type,
                "uploaded_by": "system"
            }

            document = await self.repo.add_document(
                project_id,
                document_data,
                str(file_path),
                file.filename
            )

            await self.repo.add_activity(
                project_id,
                f"Document uploaded: {data.name}",
                "document_upload",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(document)
            await self.db.commit()

            return document

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_documents(self, project_id: UUID) -> List[ProjectDocument]:
        """Get all documents for a project."""
        return await self.repo.get_documents(project_id)

    async def get_document(self, document_id: UUID) -> Optional[ProjectDocument]:
        """Get document by ID."""
        return await self.repo.get_document(document_id)

    async def update_document(self, document_id: UUID, data: ProjectDocumentUpdate) -> Optional[ProjectDocument]:
        """Update document metadata - handle transaction."""
        try:
            document = await self.repo.update_document(document_id, data.model_dump(exclude_unset=True))
            if document:
                await self.db.flush()
                await self.db.refresh(document)
                await self.db.commit()
            return document
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete document - handle transaction."""
        try:
            document = await self.repo.get_document(document_id)
            if document:
                import os
                if os.path.exists(document.file_path):
                    os.remove(document.file_path)

            result = await self.repo.delete_document(document_id)
            await self.db.flush()
            await self.db.commit()
            return result

        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== TEAM ====================

    async def add_team_member(self, project_id: UUID, data: ProjectTeamCreate) -> ProjectTeam:
        """Add team member to project - handle transaction."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")

            existing = await self.repo.get_team_member(project_id, data.user_id)
            if existing:
                raise ValidationError(
                    f"User {data.user_id} is already a team member")

            team_member = await self.repo.add_team_member(project_id, data.model_dump())

            await self.repo.add_activity(
                project_id,
                f"Team member added: {data.user_id} as {data.role}",
                "team_add",
                performed_by="system"
            )

            await self.db.flush()
            await self.db.refresh(team_member)
            await self.db.commit()

            return team_member

        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_team_members(self, project_id: UUID) -> List[ProjectTeam]:
        """Get all team members for a project."""
        return await self.repo.get_team_members(project_id)

    async def remove_team_member(self, team_member_id: UUID) -> bool:
        """Remove team member from project - handle transaction."""
        try:
            result = await self.repo.remove_team_member(team_member_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e

    async def update_team_member_role(self, team_member_id: UUID, role: str) -> Optional[ProjectTeam]:
        """Update team member role - handle transaction."""
        try:
            team_member = await self.repo.update_team_member_role(team_member_id, role)
            if team_member:
                await self.db.flush()
                await self.db.refresh(team_member)
                await self.db.commit()
            return team_member
        except Exception as e:
            await self.db.rollback()
            raise e

    # ==================== HELPERS ====================

    def _serialize_project(self, project: Project) -> Dict:
        """Convert Project object to a serializable dictionary for Kanban."""
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
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "project_start_date": project.project_start_date.isoformat() if project.project_start_date else None,
            "project_target_delivery": project.project_target_delivery.isoformat() if project.project_target_delivery else None,
            "stage": {
                "id": str(project.stage.id) if project.stage else None,
                "name": project.stage.name if project.stage else None,
                "color": project.stage.color if project.stage else None
            } if project.stage else None
        }
