"""
    Project Service - REFACTORED
    Project hanya mengelola core data : 
        - name, status, priority, progress
        - estimated_cost, actual_cost
        - timeline, tasks, labor, expenses, documents, team
    
    customer/vehicle data diambil dari inquiry via relationship
    financial summary dihitung dari multiple sources (inventory + payment)
    payment/invoice data diambil dari payment module
"""

from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path
from typing_extensions import Optional, List, Dict, Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.exceptions import NotFoundError, ValidationError, BusinessError
from core.constants import InquiryStatus, ProjectPriority, ProjectStatus

from modules.projects.models import (
    Project, ProjectDocument, ProjectStage, ProjectTask,
    ProjectLabor, ProjectActivity, ProjectExpense, 
    ProjectPriceListItem, ProjectTimeline, ProjectTeam
)

from .repository import ProjectRepository
from .schemas import (
    ProjectCreate, ProjectDocumentCreate, ProjectDocumentUpdate,
    ProjectDocumentUpload, ProjectTimelineCreate, ProjectTimelineUpdate,
    ProjectUpdate, ProjectTaskCreate, ProjectTeamCreate, ProjectLaborCreate, 
    ProjectExpenseCreate, ProjectStageCreate, ProjectFinancialSummary, ProjectMaterialSummary,
    ProjectLaborSummary
)

from modules.inquiry.repository import InquiryRepository
from modules.inventory.models import ProjectWorkshopTask, InventoryMaterialUsage
from modules.price_list.models import PriceListItem
from modules.price_list.repository import PriceListRepository
from modules.payment.repository import PaymentRepository, InvoiceRepository



class ProjectService:
    """
            Service untuk project management
        - Transaction handling di setiap method
        - Tidak ada logic payment/invoice disini
        - Customer/Vehicle data dari inquiry
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)
        self.inqury_repo = InquiryRepository(db)
        self.price_list_repo = PriceListRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        
    # ====================================================
    # HELPER METHODS
    # ====================================================
    
    async def _generate_project_code(self) -> str:
        """ Generate unique project code : PRJ ---XX--xxx"""
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")
        
        # get last sequence for this month
        stmt = select(func.max(Project.project_code).where(Project.project_code.ilike(f"NKTPR-{year}{month}-%")))
        result = await self.db.execute(stmt)
        last_code = result.scalar()
        if last_code: 
            parts = last_code.split("-")
            if len(parts) == 5:
                try:
                    seq = int(parts[4])
                    seq += 1
                except ValueError:
                    seq = 1
            else:
                seq = 1
        else:
            seq = 1
            
        return f"NKTPR-{year}{month}-{str(seq).zfill(4)}"

    async def _sync_from_inquiry(self, project: Project, inquiry_id: UUID) -> Project:
        """Sync denormalized fields from inquiry"""
        inquiry = await self.inqury_repo.get(inquiry_id)
        if not inquiry:
            return project
        
        project.customer_name = inquiry.customer_name
        project.customer_phone = inquiry.customer_phone_number
        project.customer_email = inquiry.customer_email
        project.customer_address = getattr(inquiry, "address", None)
        project.vehicle_brand = inquiry.vehicle_brand
        project.vehicle_model = inquiry.vehicle_model
        project.vehicle_year = inquiry.vehicle_year
        project.vehicle_license_plate = inquiry.vehicle_license_plate
        project.source = getattr(inquiry, 'source', 'inquiry')
        
        return project
    
    # =====================================================
    # CRUD OPERATIONS
    # =====================================================
    
    async def create(self, data: ProjectCreate) -> Project:
        """
            Create new Project
                - Auto-populate from inquiry if inquiry_id provided
                - Auto-generate project_code
                - Auto-create workshop job
                - Update inquiry status to CONVERTED
        """
        try: 
            # 1. Prepare project data
            project_data = data.model_dump(exclude_unset=True, exclude={"price_list_item_ids"})
            
            # 2. Set defaults
            if not project_data.get("priority"):
                project_data['priority'] = ProjectPriority.MEDIUM
                
            # 3. Generate project code
            project_data['project_code'] = await self._generate_project_code()
            
            # 4. Create Project
            project = Project(**project_data)
            self.db.add(project)
            await self.db.flush()
            
            # 5. Sync from inquiry if provided
            if data.inquiry_id:
                project = await self._sync_from_inquiry(project, data.inquiry_id)
                
            # 6. Calculate estimated cost from price list items
            if data.price_list_item_ids:
                estimated_cost = Decimal(0)
                for item_id in data.price_list_item_ids:
                    price_item = await self.price_list_repo.get(item_id)
                    if price_item:
                        estimated_cost += price_item.price
                        # add junction table
                        project_price_item = ProjectPriceListItem(
                            project=project.id,
                            price_list_item_id=item_id, quantity=Decimal(1),
                            unit_price_at_usage=price_item.price,
                            total_price=price_item.price
                        )
                        self.db.add(project_price_item)
                    else:
                        raise ValidationError(f"Price list item '{item_id}' not found")
                    
                project.estimated_cost = estimated_cost
                
            # 7. auto create  workshop jobs
            job = ProjectWorkshopTask(project_id=project.id, unit_name=project.name, status="pending", estimated_cost=project.estimated_cost or Decimal(0))
            self.db.add(job)
            
            # 8. Add activity
            await self.repo.add_activity(project.id, f"Project created : {project.name} ({project.project_code})", "creation", performed_by="sysadmin")
            
            # 9. update inquiry if linked
            if data.inquiry_id:
                inquiry = await self.inquiry_repo.get(data.inquiry_id)
                if inquiry and inquiry.status != InquiryStatus.CONVERTED:
                    inquiry.status = InquiryStatus.CONVERTED
                    inquiry.converted_at = datetime.now()
                    await self.inquiry_repo.add_activity(data.inquiry_id, f"Converted to project : {project.project_code} - {project.name}", "conversion", performed_by="sysadmin")
                    
            await self.db.flush()
            await self.db.refresh(project)
            await self.db.commit()
            
            return project
        except Exception as e:
            await self.db.rollback()
            raise e
        
    async def get(self, project_id: UUID) -> Optional[Project]:
        """Get Project by ID with all details"""
        return await self.repo.get_with_details(project_id)
    
    async def get_by_inquiry(self, inquiry_id: UUID) -> Optional[Project]:
        """Get project by inquiry ID."""
        return await self.repo.get_by_inquiry(inquiry_id)

    async def get_by_code(self, project_code: str) -> Optional[Project]:
        """Get project by project code."""
        return await self.repo.get_by_code(project_code)
    
    async def list_all(
        self, status: Optional[str] = None, priority: Optional[str] = None, 
        brand: Optional[str] = None, search: Optional[str] = None,
        is_archived: bool = False, stage_id: Optional[UUID] = None, 
        limit: int = 10, offset: int = 0
    ) -> tuple[List[Project], int]:
        """List all project with filters"""
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
        """Update a Project"""
        try:
            update_data = data.model_dump(exclude_unset=True)
            project = await self.repo.update(project_id, update_data)
            if project:
                await self.repo.add_activity(project_id, "Project Updated", "update", performed_by="sysadmin")
                await self.db.flush()
                await self.db.refresh(project)
                await self.db.commit()
            
            return project
        except Exception as e:
            await self.db.rollback()
            raise e
        
    async def delete(self, project_id: UUID) -> bool:
        """Delete a project."""
        try:
            result = await self.repo.delete(project_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e
        
    async def archive(self, project_id: UUID) -> bool:
        """Archive a project."""
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
        """Unarchive a project."""
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
        
    # ============================================================
    # STATUS & PROGRESS
    # ============================================================
    
    async def update_status(self, project_id: UUID, status: str, note: Optional[str] = None) -> Optional[Project]:
        """Update project status."""
        try:
            valid_statuses = [e.value for e in ProjectStatus]
            if status not in valid_statuses:
                raise ValidationError(f"Invalid project status: {status}")
            
            project = await self.repo.update_status(project_id, status, note)
            
            if project:
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
        """Update project progress."""
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
        """
        Complete a project.
        
        ✅ Update project status to COMPLETED
        ✅ Update inquiry status to COMPLETED
        ✅ Does NOT handle payment/invoice (handled by Payment module)
        """
        try:
            project = await self.repo.get_with_details(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")
            
            # Check if already completed
            if project.status == ProjectStatus.COMPLETED:
                raise BusinessError("Project is already completed")
            
            # Update project
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
            
            # Update inquiry if linked
            if project.inquiry_id:
                inquiry = await self.inquiry_repo.get(project.inquiry_id)
                if inquiry and inquiry.status != InquiryStatus.COMPLETED:
                    inquiry.status = InquiryStatus.COMPLETED
                    await self.inquiry_repo.add_activity(
                        project.inquiry_id,
                        f"Project {project.project_code} completed, inquiry auto-updated",
                        "auto_update",
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
        """Cancel a project."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")
            
            if project.status in [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]:
                raise BusinessError(f"Cannot cancel project with status: {project.status}")
            
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
        
    # ============================================================
    # FINANCIAL SUMMARY (Aggregate dari multiple sources)
    # ============================================================
    
    async def get_financial_summary(self, project_id: UUID) -> ProjectFinancialSummary:
        """
        Get comprehensive financial summary for a project.
        
        ✅ Data diambil dari:
        - Project (estimated_cost, actual_cost)
        - Inventory (material usage)
        - Project Labor
        - Project Expenses
        - Payment module (total_paid, deposit_paid)
        """
        project = await self.repo.get_with_details(project_id)
        if not project:
            raise NotFoundError(f"Project {project_id} not found")
        
        # 1. Material cost dari inventory
        material_cost = Decimal(0)
        material_usages = []
        
        if project.workshop_job:
            for usage in project.workshop_job.material_usages:
                if usage.item:
                    unit_cost = usage.unit_cost or Decimal(0)
                    total = usage.quantity * unit_cost
                    material_cost += total
                    material_usages.append(ProjectMaterialSummary(
                        id=usage.id,
                        item_name=usage.item.name,
                        item_category=usage.item.category,
                        quantity=usage.quantity,
                        unit=usage.item.unit,
                        unit_cost=unit_cost,
                        total_cost=total,
                        is_waste=usage.is_waste
                    ))
        
        # 2. Labor cost dari project labor items
        labor_cost = Decimal(0)
        labor_items = []
        for labor in project.labor_items:
            labor_cost += labor.total_cost
            labor_items.append(ProjectLaborSummary(
                labor_type=labor.labor_type,
                hours=labor.hours,
                rate_per_hour=labor.rate_per_hour,
                total_cost=labor.total_cost,
                technician=labor.technical_name
            ))
        
        # 3. Expenses
        expenses_total = Decimal(0)
        for exp in project.expenses:
            expenses_total += exp.amount
        
        # 4. Actual cost = material + labor + expenses
        actual_cost = material_cost + labor_cost + expenses_total
        project.actual_cost = actual_cost
        
        # 5. Payment summary (dari Payment module)
        total_paid = Decimal(0)
        deposit_paid = Decimal(0)
        
        if project.inquiry_id:
            payments = await self.payment_repo.get_by_inquiry(project.inquiry_id)
            for p in payments:
                if p.status == "completed":
                    total_paid += p.amount
                    if p.payment_type == "deposit":
                        deposit_paid += p.amount
        
        # 6. Calculate derived values
        estimated_cost = project.estimated_cost or Decimal(0)
        profit = total_paid - actual_cost
        margin = (profit / total_paid * 100) if total_paid > 0 else Decimal(0)
        remaining_balance = actual_cost - total_paid
        
        await self.db.flush()
        
        return ProjectFinancialSummary(
            estimated_cost=float(estimated_cost),
            actual_cost=float(actual_cost),
            material_cost=float(material_cost),
            labor_cost=float(labor_cost),
            expenses=float(expenses_total),
            total_paid=float(total_paid),
            deposit_paid=float(deposit_paid),
            remaining_balance=float(max(remaining_balance, Decimal(0))),
            profit=float(profit),
            margin=float(round(margin, 2)),
            material_usages=material_usages,
            labor_items=labor_items
        )

    async def get_financial_summary_all(self) -> Dict[str, Any]:
        """Get financial summary for all projects."""
        return await self.repo.get_financial_summary()
    
    # ============================================================
    # TASKS
    # ============================================================
    
    async def add_task(self, project_id: UUID, task_data: Dict[str, Any]) -> ProjectTask:
        """Add a task to project."""
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
        """Update a task."""
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
        """Delete a task."""
        try:
            result = await self.repo.delete_task(task_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e
        
    async def complete_task(self, task_id: UUID) -> Optional[ProjectTask]:
        """Mark a task as completed."""
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
        
    # ============================================================
    # LABOR
    # ============================================================
    
    
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
        """Add labor to project."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")
            
            # Get rate from price list if not provided
            if rate_per_hour is None:
                rate_per_hour = await self._get_labor_rate(labor_type)
                if rate_per_hour is None:
                    raise ValidationError(
                        f"Labor type '{labor_type}' not found in price list. "
                        "Please provide rate_per_hour manually."
                    )
            
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
            project.actual_cost = (project.actual_cost or Decimal(0)) + total_cost
            
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
        
    async def _get_labor_rate(self, labor_type: str) -> Optional[Decimal]:
        """Get labor rate from price list."""
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
        return price_item.price if price_item else None
    
    async def get_labor_items(self, project_id: UUID) -> List[ProjectLabor]:
        """Get all labor items for a project."""
        return await self.repo.get_labor_items(project_id)
    
    async def delete_labor(self, labor_id: UUID) -> bool:
        """Delete a labor item."""
        try:
            labor = await self.repo.get_labor_item(labor_id)
            if labor:
                project = await self.repo.get(labor.project_id)
                if project:
                    project.actual_cost = (project.actual_cost or Decimal(0)) - labor.total_cost
            
            result = await self.repo.delete_labor(labor_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e
        
        
    # ============================================================
    # EXPENSES
    # ============================================================
    
    
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
        """Add an expense to project."""
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
            
            project.actual_cost = (project.actual_cost or Decimal(0)) + amount
            
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
        """Approve an expense."""
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
        
    # ============================================================
    # PRICE LIST ITEMS
    # ============================================================
    
    async def add_price_list_item(
        self,
        project_id: UUID,
        price_list_item_id: UUID,
        quantity: Decimal = Decimal(1),
        notes: Optional[str] = None
    ) -> ProjectPriceListItem:
        """Add a price list item to project."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")
            
            price_item = await self.price_list_repo.get(price_list_item_id)
            if not price_item:
                raise NotFoundError(f"Price list item {price_list_item_id} not found")
            
            if not price_item.is_active:
                raise ValidationError(f"Price list item '{price_item.name}' is not active")
            
            item = await self.repo.add_price_list_item(
                project_id=project_id,
                price_list_item_id=price_list_item_id,
                quantity=quantity,
                unit_price=price_item.price,
                notes=notes
            )
            
            project.estimated_cost = (project.estimated_cost or Decimal(0)) + item.total_price
            
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
        """Remove a price list item from project."""
        try:
            item = await self.repo.get_price_list_item(item_id)
            if not item:
                return False
            
            project = await self.repo.get(item.project_id)
            if project:
                project.estimated_cost = (project.estimated_cost or Decimal(0)) - item.total_price
            
            result = await self.repo.remove_price_list_item(item_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e
        
    # ============================================================
    # STAGES
    # ============================================================
    
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
        """Create a new project stage."""
        try:
            existing_stages = await self.repo.get_stages(active_only=False)
            for stage in existing_stages:
                if stage.name.lower() == data.get("name", "").lower():
                    raise ValidationError(f"Stage '{data.get('name')}' already exists")
            
            stage = await self.repo.create_stage(data)
            await self.db.flush()
            await self.db.refresh(stage)
            await self.db.commit()
            return stage
        except Exception as e:
            await self.db.rollback()
            raise e
        
    # ============================================================
    # ACTIVITIES
    # ============================================================

    async def get_activities(self, project_id: UUID, limit: int = 50) -> List[ProjectActivity]:
        """Get all activities for a project."""
        return await self.repo.get_activities(project_id, limit)
    

    # ============================================================
    # TIMELINE
    # ============================================================

    async def add_timeline(self, project_id: UUID, data: ProjectTimelineCreate) -> ProjectTimeline:
        """Add timeline to project."""
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
        """Update timeline."""
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
        """Mark timeline as completed."""
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
        """Delete timeline."""
        try:
            result = await self.repo.delete_timeline(timeline_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e
        
    # ============================================================
    # DOCUMENTS
    # ============================================================

    async def upload_document(
        self,
        project_id: UUID,
        file: UploadFile,
        data: ProjectDocumentUpload
    ) -> ProjectDocument:
        """Upload document to project."""
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

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete document."""
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

    # ============================================================
    # TEAM
    # ============================================================

    async def add_team_member(self, project_id: UUID, data: ProjectTeamCreate) -> ProjectTeam:
        """Add team member to project."""
        try:
            project = await self.repo.get(project_id)
            if not project:
                raise NotFoundError(f"Project {project_id} not found")
            
            existing = await self.repo.get_team_member(project_id, data.user_id)
            if existing:
                raise ValidationError(f"User {data.user_id} is already a team member")
            
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
        """Remove team member from project."""
        try:
            result = await self.repo.remove_team_member(team_member_id)
            await self.db.flush()
            await self.db.commit()
            return result
        except Exception as e:
            await self.db.rollback()
            raise e

    async def update_team_member_role(self, team_member_id: UUID, role: str) -> Optional[ProjectTeam]:
        """Update team member role."""
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
        
    # ============================================================
    # DASHBOARD
    # ============================================================

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
    
    # ============================================================
    # HELPERS
    # ============================================================

    def _serialize_project(self, project: Project) -> Dict:
        """Convert Project object to serializable dictionary for Kanban."""
        return {
            "id": str(project.id),
            "inquiry_id": str(project.inquiry_id) if project.inquiry_id else None,
            "name": project.name,
            "project_code": project.project_code,
            "customer_name": project.customer_name,
            "customer_phone": project.customer_phone,
            "vehicle_brand": project.vehicle_brand,
            "vehicle_model": project.vehicle_model,
            "status": project.status,
            "priority": project.priority,
            "progress": project.progress or 0,
            "estimated_cost": float(project.estimated_cost or 0),
            "actual_cost": float(project.actual_cost or 0),
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "project_start_date": project.project_start_date.isoformat() if project.project_start_date else None,
            "project_target_delivery": project.project_target_delivery.isoformat() if project.project_target_delivery else None,
            "stage": {
                "id": str(project.stage.id) if project.stage else None,
                "name": project.stage.name if project.stage else None,
                "color": project.stage.color if project.stage else None
            } if project.stage else None
        }