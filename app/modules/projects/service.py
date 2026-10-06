"""Business rules for the projects module.

The CostingService is the core: it knows how to turn activities
(materials used, labor hours, outsourcing, overhead) into money.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.inventory.constants import (
    ReferenceType,
    TransactionType,
)
from app.modules.inventory.models import InventoryTransaction
from app.modules.inventory.repository import MaterialRepository
from app.modules.projects.constants import (
    ALLOWED_PROJECT_TRANSITIONS,
    COST_CATEGORY_LABELS,
    CostCategory,
    INVENTORY_CATEGORIES,
    LABOR_CATEGORIES,
    ProjectStatus,
    SETTING_MONTHLY_LABOR_HOURS,
    SETTING_MONTHLY_OVERHEAD,
    TERMINAL_PROJECT_STATUSES,
)
from app.modules.projects.models import Employee, Project, ProjectItem
from app.modules.projects.repository import (
    EmployeeRepository,
    ProjectRepository,
)
from app.modules.projects.schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    ProjectCreate,
    ProjectItemCreate,
    ProjectItemUpdate,
    ProjectUpdate,
)
from app.modules.settings.service import SettingsService


# ════════════════════════════════════════════════════════════════
# EMPLOYEES
# ════════════════════════════════════════════════════════════════

class EmployeeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmployeeRepository(db)
        self.audit = AuditService(db)

    async def create(self, payload: EmployeeCreate, *, actor: User) -> Employee:
        if await self.repo.by_code(payload.code):
            raise ConflictError(f"Employee code already exists: {payload.code}")
        emp = Employee(**payload.model_dump())
        await self.repo.add(emp)
        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="employees",
            record_id=emp.id,
            user_id=actor.id,
            new_data={"code": emp.code, "name": emp.name},
        )
        return emp

    async def update(
        self, eid: UUID, payload: EmployeeUpdate, *, actor: User
    ) -> Employee:
        emp = await self._get_or_404(eid)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(emp, field, value)
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="employees",
            record_id=emp.id,
            user_id=actor.id,
            new_data={"name": emp.name, "hourly_rate": float(emp.hourly_rate)},
        )
        return emp

    async def _get_or_404(self, eid: UUID) -> Employee:
        emp = await self.repo.get(eid)
        if not emp:
            raise NotFoundError("Employee not found")
        return emp


# ════════════════════════════════════════════════════════════════
# COSTING ENGINE
# ════════════════════════════════════════════════════════════════

@dataclass
class CostInputs:
    """Resolved inputs the caller provides for computing a cost."""

    category: str
    quantity: float
    unit_cost: float


class CostingService:
    """
    Computes HPP from cost inputs.

    Overhead rate = monthly_overhead / monthly_labor_hours (from settings).
    Material consumption creates InventoryTransaction(CONSUMPTION).
    Every project total is denormalized on the Project row and kept in sync
    by `recalc_project_totals`.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.materials = MaterialRepository(db)
        self.employees = EmployeeRepository(db)
        self.settings = SettingsService(db)
        self.audit = AuditService(db) 

    async def overhead_rate_per_hour(self) -> float:
        overhead = await self.settings.get_value(SETTING_MONTHLY_OVERHEAD, "0")
        hours = await self.settings.get_value(SETTING_MONTHLY_LABOR_HOURS, "0")
        try:
            o = float(overhead or 0)
            h = float(hours or 0)
        except (TypeError, ValueError):
            return 0.0
        return o / h if h > 0 else 0.0

    async def resolve_unit_cost(
        self,
        *,
        category: str,
        material_id: UUID | None,
        employee_id: UUID | None,
        provided_unit_cost: float | None,
    ) -> float:
        """
        Determine the unit cost for a line item.

        - MATERIAL / PART: from the material's `cost_per_stock_unit`
        - LABOR: from the employee's `hourly_rate`
        - OVERHEAD: computed from settings
        - OUTSOURCE / MISC: from provided_unit_cost (or 0)
        """
        if category in INVENTORY_CATEGORIES:
            if not material_id:
                raise ValidationError(
                    f"material_id is required for {COST_CATEGORY_LABELS.get(category, category)} items"
                )
            material = await self.materials.get(material_id)
            if not material:
                raise NotFoundError("Material not found")
            return float(material.cost_per_stock_unit)

        if category in LABOR_CATEGORIES:
            if not employee_id:
                raise ValidationError("employee_id is required for labor items")
            emp = await self.employees.get(employee_id)
            if not emp:
                raise NotFoundError("Employee not found")
            return float(emp.hourly_rate)

        if category == CostCategory.OVERHEAD.value:
            return await self.overhead_rate_per_hour()

        # OUTSOURCE and MISC: whatever the caller supplied
        return provided_unit_cost or 0.0

    # ── Project item operations ────────────────────────

    async def add_item(
        self,
        project_id: UUID,
        payload: ProjectItemCreate,
        *,
        actor: User,
    ) -> ProjectItem:
        project = await self._get_project_or_404(project_id)
        if project.status in TERMINAL_PROJECT_STATUSES:
            raise ConflictError(f"Cannot add items to a {project.status} project")

        # Resolve unit cost from the category
        est_unit_cost = await self.resolve_unit_cost(
            category=payload.category,
            material_id=payload.material_id,
            employee_id=payload.employee_id,
            provided_unit_cost=payload.estimated_unit_cost,
        )

        item = ProjectItem(
            project_id=project.id,
            category=payload.category,
            description=payload.description,
            material_id=payload.material_id,
            employee_id=payload.employee_id,
            unit=payload.unit,
            estimated_quantity=payload.estimated_quantity,
            estimated_unit_cost=est_unit_cost,
            estimated_cost=float(payload.estimated_quantity or 0) * est_unit_cost,
            actual_quantity=payload.actual_quantity,
            actual_unit_cost=payload.actual_unit_cost,
            notes=payload.notes,
        )
        await self.projects.add_item(item)
        await self._sync_actual_cost(item)
        await self.recalc_project_totals(project_id)
        await self.audit.log(
            action=AuditAction.COST_ENTRY,
            table_name="project_items",
            record_id=item.id,
            user_id=actor.id,
            new_data={
                "project_id": str(project_id),
                "category": item.category,
                "estimated_cost": float(item.estimated_cost),
            },
        )
        return item

    async def update_item(
        self,
        project_id: UUID,
        item_id: UUID,
        payload: ProjectItemUpdate,
        *,
        actor: User,
    ) -> ProjectItem:
        project = await self._get_project_or_404(project_id)
        if project.status in TERMINAL_PROJECT_STATUSES:
            raise ConflictError(f"Cannot edit items on a {project.status} project")

        item = await self._get_item_or_404(project_id, item_id)

        # ── Capture the OLD quantity BEFORE we mutate the item ──
        old_actual_qty = float(item.actual_quantity or 0)

        for field, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(item, field, value)

        # Re-resolve estimated unit cost if the category's source changed
        if item.category in INVENTORY_CATEGORIES or item.category in LABOR_CATEGORIES:
            resolved = await self.resolve_unit_cost(
                category=item.category,
                material_id=item.material_id,
                employee_id=item.employee_id,
                provided_unit_cost=item.estimated_unit_cost,
            )
            item.estimated_unit_cost = resolved

        # Recompute estimated cost
        item.estimated_cost = float(item.estimated_quantity or 0) * float(item.estimated_unit_cost or 0)

        # Recompute actual cost and sync inventory consumption with the correct delta
        await self._sync_actual_cost(item, previous_actual_qty=old_actual_qty)
        await self.recalc_project_totals(project_id)
        await self.audit.log(
            action=AuditAction.COST_ENTRY,
            table_name="project_items",
            record_id=item.id,
            user_id=actor.id,
            new_data={"project_id": str(project_id), "updated": True},
        )
        return item

    async def delete_item(
        self, project_id: UUID, item_id: UUID, *, actor: User
    ) -> None:
        project = await self._get_project_or_404(project_id)
        if project.status in TERMINAL_PROJECT_STATUSES:
            raise ConflictError(f"Cannot delete items from a {project.status} project")

        item = await self._get_item_or_404(project_id, item_id)

        # If the item had a material consumption, reverse it
        if item.material_id and item.actual_quantity:
            await self._record_inventory_adjustment(
                project=project,
                item=item,
                quantity=-float(item.actual_quantity),
                reason="Item deleted — consumption reversed",
                actor=actor,
            )

        await self.projects.delete_item(item)
        await self.recalc_project_totals(project_id)

    # ── Internal helpers ───────────────────────────────

    async def _sync_actual_cost(
        self,
        item: ProjectItem,
        previous_actual_qty: float | None = None,
    ) -> None:
        """
        Compute actual_cost from actual_quantity and actual_unit_cost.
        If the item is a material, sync the inventory ledger with the delta.
        """
        actual_unit_cost = float(item.actual_unit_cost or item.estimated_unit_cost or 0)
        item.actual_unit_cost = actual_unit_cost
        item.actual_cost = float(item.actual_quantity or 0) * actual_unit_cost

        # Sync inventory if the material is tracked
        if item.material_id:
            old_qty = previous_actual_qty if previous_actual_qty is not None else 0.0
            new_qty = float(item.actual_quantity or 0)
            delta = new_qty - old_qty
            if abs(delta) > 1e-6:
                project = await self.projects.get(item.project_id)
                if project:
                    await self._record_inventory_adjustment(
                        project=project,
                        item=item,
                        quantity=delta,
                        reason="Project item consumption update",
                        actor=None,
                    )

    async def _record_inventory_adjustment(
        self,
        *,
        project: Project,
        item: ProjectItem,
        quantity: float,
        reason: str,
        actor: User | None,
    ) -> None:
        """
        Create an inventory transaction.

        Positive `quantity` means more was consumed → CONSUMPTION.
        Negative `quantity` means reversing → ADJUSTMENT_IN.
        """
        if quantity > 0:
            tx_type = TransactionType.CONSUMPTION.value
            qty = quantity
        else:
            tx_type = TransactionType.ADJUSTMENT_IN.value
            qty = -quantity

        unit_cost = float(item.actual_unit_cost or item.estimated_unit_cost or 0)
        tx = InventoryTransaction(
            material_id=item.material_id,
            transaction_type=tx_type,
            quantity=qty,
            unit_cost=unit_cost,
            reference_type=ReferenceType.PROJECT.value,
            reference_id=project.id,
            reference_note=f"{project.code} — {item.description[:80]}",
            notes=reason,
            created_by_id=actor.id if actor else None,
        )
        self.db.add(tx)
        await self.db.flush()

    async def recalc_project_totals(self, project_id: UUID) -> Project:
        """
        Recompute every denormalized total on the Project row from its items.
        """
        project = await self._get_project_or_404(project_id)
        items = await self.projects.list_items(project_id)

        # Reset
        totals = {
            "estimated_materials": 0.0, "estimated_parts": 0.0,
            "estimated_labor": 0.0, "estimated_outsource": 0.0,
            "estimated_overhead": 0.0, "estimated_misc": 0.0,
            "actual_materials": 0.0, "actual_parts": 0.0,
            "actual_labor": 0.0, "actual_outsource": 0.0,
            "actual_overhead": 0.0, "actual_misc": 0.0,
        }

        mapping = {
            CostCategory.MATERIAL.value: "materials",
            CostCategory.PART.value: "parts",
            CostCategory.LABOR.value: "labor",
            CostCategory.OUTSOURCE.value: "outsource",
            CostCategory.OVERHEAD.value: "overhead",
            CostCategory.MISC.value: "misc",
        }

        for item in items:
            key = mapping.get(item.category)
            if not key:
                continue
            totals[f"estimated_{key}"] += float(item.estimated_cost or 0)
            totals[f"actual_{key}"] += float(item.actual_cost or 0)

        project.estimated_materials = totals["estimated_materials"]
        project.estimated_parts = totals["estimated_parts"]
        project.estimated_labor = totals["estimated_labor"]
        project.estimated_outsource = totals["estimated_outsource"]
        project.estimated_overhead = totals["estimated_overhead"]
        project.estimated_misc = totals["estimated_misc"]

        project.actual_materials = totals["actual_materials"]
        project.actual_parts = totals["actual_parts"]
        project.actual_labor = totals["actual_labor"]
        project.actual_outsource = totals["actual_outsource"]
        project.actual_overhead = totals["actual_overhead"]
        project.actual_misc = totals["actual_misc"]

        project.estimated_hpp = sum(totals[k] for k in totals if k.startswith("estimated_"))
        project.actual_hpp = sum(totals[k] for k in totals if k.startswith("actual_"))

        await self.db.flush()
        return project

    async def _get_project_or_404(self, pid: UUID) -> Project:
        project = await self.projects.get(pid)
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def _get_item_or_404(self, project_id: UUID, item_id: UUID) -> ProjectItem:
        item = await self.projects.get_item(item_id)
        if not item or item.project_id != project_id:
            raise NotFoundError("Project item not found")
        return item


# ════════════════════════════════════════════════════════════════
# PROJECT SERVICE — CRUD and workflow
# ════════════════════════════════════════════════════════════════

class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProjectRepository(db)
        self.audit = AuditService(db)
        self.costing = CostingService(db)

    async def create(
        self, payload: ProjectCreate, *, actor: User
    ) -> Project:
        # Validate references
        from app.modules.customers.repository import CustomerRepository
        from app.modules.vehicles.repository import VehicleRepository

        if not await CustomerRepository(self.db).get(payload.customer_id):
            raise NotFoundError("Customer not found")
        if payload.vehicle_id and not await VehicleRepository(self.db).get(payload.vehicle_id):
            raise NotFoundError("Vehicle not found")
        if payload.inquiry_id:
            from app.modules.inquiries.repository import InquiryRepository
            if not await InquiryRepository(self.db).get(payload.inquiry_id):
                raise NotFoundError("Inquiry not found")

        project = Project(
            code=await self.repo.next_code(),
            title=payload.title,
            description=payload.description,
            inquiry_id=payload.inquiry_id,
            customer_id=payload.customer_id,
            vehicle_id=payload.vehicle_id,
            assigned_lead_id=payload.assigned_lead_id,
            status=ProjectStatus.ESTIMATING.value,
            priority=payload.priority,
            quoted_price=payload.quoted_price,
            approved_price=payload.approved_price,
            start_date=payload.start_date,
            target_end_date=payload.target_end_date,
            internal_notes=payload.internal_notes,
            created_by_id=actor.id,
        )
        await self.repo.add(project)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="projects",
            record_id=project.id,
            user_id=actor.id,
            new_data={
                "code": project.code,
                "customer_id": str(payload.customer_id),
                "inquiry_id": str(payload.inquiry_id) if payload.inquiry_id else None,
            },
        )
        return project

    async def update(
        self, pid: UUID, payload: ProjectUpdate, *, actor: User
    ) -> Project:
        project = await self._get_or_404(pid)
        if project.status in TERMINAL_PROJECT_STATUSES:
            raise ConflictError(f"Cannot edit a {project.status} project")

        for field, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(project, field, value)

        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="projects",
            record_id=project.id,
            user_id=actor.id,
            new_data={"code": project.code},
        )
        return project

    async def change_status(
        self, pid: UUID, new_status: str, *, note: str | None, actor: User
    ) -> Project:
        project = await self._get_or_404(pid)
        current = project.status

        allowed = ALLOWED_PROJECT_TRANSITIONS.get(current, frozenset())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot move project from {current} to {new_status}",
                context={"current": current, "target": new_status, "allowed": sorted(allowed)},
            )

        project.status = new_status

        if new_status == ProjectStatus.APPROVED.value and project.approved_price is None:
            project.approved_price = project.quoted_price

        if new_status == ProjectStatus.DELIVERED.value:
            project.actual_end_date = datetime.now(UTC).date()

        if note:
            existing = project.closing_note or ""
            project.closing_note = f"{existing}\n[{current} → {new_status}] {note}".strip()

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="projects",
            record_id=project.id,
            user_id=actor.id,
            old_data={"status": current},
            new_data={"status": new_status, "note": note},
        )

        # ── Pricing snapshots ────────────────────────
        # When a project is APPROVED, freeze the pricing decision.
        # When DELIVERED, update with actual margin.
        if new_status == ProjectStatus.APPROVED.value:
            await self._record_approval_snapshot(project, actor=actor)

        if new_status == ProjectStatus.DELIVERED.value:
            await self._update_delivery_snapshot(project, actor=actor)

        return project

    # ── Snapshot helpers ────────────────────────────

    async def _record_approval_snapshot(self, project, *, actor: User) -> None:
        """Record a pricing snapshot when the project is approved."""
        from app.modules.inquiries.repository import InquiryRepository
        from app.modules.pricing.schemas import PricingSnapshotCreate
        from app.modules.pricing.service import PricingService

        hpp = float(project.actual_hpp or project.estimated_hpp or 0)
        if hpp <= 0:
            return  # nothing meaningful to snapshot

        # Get service + category for rule matching
        service_interest = None
        vehicle_category = None
        if project.inquiry_id:
            inq = await InquiryRepository(self.db).get(project.inquiry_id)
            if inq:
                service_interest = inq.service_interest
        if project.vehicle_id:
            from app.modules.vehicles.repository import VehicleRepository
            v = await VehicleRepository(self.db).get(project.vehicle_id)
            if v:
                vehicle_category = v.category

        await PricingService(self.db).record_snapshot(
            PricingSnapshotCreate(
                project_id=project.id,
                inquiry_id=project.inquiry_id,
                service_interest=service_interest,
                vehicle_category=vehicle_category,
                hpp_estimate=hpp,
                actual_quoted_price=(
                    float(project.approved_price)
                    if project.approved_price
                    else (float(project.quoted_price) if project.quoted_price else None)
                ),
                notes=f"Snapshot at approval. Status transitioned to {ProjectStatus.APPROVED.value}.",
            ),
            actor=actor,
        )

    async def _update_delivery_snapshot(self, project, *, actor: User) -> None:
        """
        On delivery, update the most recent snapshot with the final HPP.
        Actual HPP may have changed since approval.
        """
        from sqlalchemy import select
        from app.modules.pricing.models import PricingSnapshot

        # Find the most recent snapshot for this project
        stmt = (
            select(PricingSnapshot)
            .where(PricingSnapshot.project_id == project.id)
            .order_by(PricingSnapshot.created_at.desc())
            .limit(1)
        )
        snap = (await self.db.execute(stmt)).scalar_one_or_none()
        if not snap:
            return

        # Refresh with final numbers
        final_hpp = float(project.actual_hpp or snap.hpp_estimate)
        final_price = (
            float(project.approved_price)
            if project.approved_price
            else (float(project.quoted_price) if project.quoted_price else None)
        )

        snap.hpp_estimate = final_hpp
        snap.actual_quoted_price = final_price
        if final_price and final_hpp > 0:
            from app.modules.pricing.service import margin_of
            snap.actual_margin_pct = margin_of(final_price, final_hpp)
        snap.notes = (snap.notes or "") + f"\n[DELIVERED] Final HPP: {final_hpp}, final price: {final_price}."

        await self.db.flush()

    async def _get_or_404(self, pid: UUID) -> Project:
        p = await self.repo.get(pid)
        if not p:
            raise NotFoundError("Project not found")
        return p