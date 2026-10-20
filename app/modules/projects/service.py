"""Business rules for the projects module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import log
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
    PROJECT_STATUSES,
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
    _validate_item_links,
)
from app.modules.settings.service import SettingsService


def _today_local() -> "datetime.date":
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _effective_unit_cost(item: ProjectItem) -> float:
    """Return actual_unit_cost if explicitly set (even if 0), else estimated."""
    if item.actual_unit_cost is not None:
        return float(item.actual_unit_cost)
    return float(item.estimated_unit_cost or 0)


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
        for field in payload.model_fields_set:
            setattr(emp, field, getattr(payload, field))
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

    Ledger consistency rules for `update_item`:
    - Quantity-only change (unit_cost unchanged, material unchanged):
      delta adjustment (efficient).
    - Material swap OR unit_cost change: reverse the full old consumption
      and re-consume at the new values, so the inventory ledger always
      reconciles with the project item's `actual_cost`.
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
        if category in INVENTORY_CATEGORIES:
            if not material_id:
                raise ValidationError(
                    f"material_id is required for "
                    f"{COST_CATEGORY_LABELS.get(category, category)} items"
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

        _validate_item_links(payload.category, payload.material_id, payload.employee_id)

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
            occurred_at=datetime.now(UTC),
        )
        await self.projects.add_item(item)
        await self._sync_actual_cost(item, actor=actor)
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

        # Capture pre-update state
        old_actual_qty = float(item.actual_quantity or 0)
        old_material_id = item.material_id
        old_actual_unit_cost = _effective_unit_cost(item)

        for field in payload.model_fields_set:
            setattr(item, field, getattr(payload, field))

        try:
            _validate_item_links(item.category, item.material_id, item.employee_id)
        except ValueError as e:
            raise ValidationError(str(e)) from e

        if item.category in INVENTORY_CATEGORIES or item.category in LABOR_CATEGORIES:
            resolved = await self.resolve_unit_cost(
                category=item.category,
                material_id=item.material_id,
                employee_id=item.employee_id,
                provided_unit_cost=item.estimated_unit_cost,
            )
            item.estimated_unit_cost = resolved

        item.estimated_cost = (
            float(item.estimated_quantity or 0) * float(item.estimated_unit_cost or 0)
        )

        new_material_id = item.material_id
        new_actual_unit_cost = _effective_unit_cost(item)

        material_swapped = old_material_id != new_material_id
        unit_cost_changed = (
            not material_swapped
            and old_material_id is not None
            and abs(new_actual_unit_cost - old_actual_unit_cost) > 1e-6
        )

        if material_swapped:
            # Reverse old consumption on the old material, then consume
            # fully on the new material at its current cost.
            if old_material_id and old_actual_qty:
                await self._record_inventory_adjustment(
                    project=project,
                    material_id=old_material_id,
                    quantity=-old_actual_qty,
                    unit_cost=old_actual_unit_cost,
                    reason="Material changed — reversing previous consumption",
                    description=item.description,
                    actor=actor,
                )
            await self._sync_actual_cost(
                item, actor=actor, previous_actual_qty=0.0,
            )
        elif unit_cost_changed:
            # Full reverse-and-reconsume so the inventory ledger reconciles
            # with the project item's `actual_cost`. A delta-only adjustment
            # here would leave the ledger and the item in disagreement.
            if old_actual_qty:
                await self._record_inventory_adjustment(
                    project=project,
                    material_id=old_material_id,
                    quantity=-old_actual_qty,
                    unit_cost=old_actual_unit_cost,
                    reason="Unit cost changed — reversing previous consumption",
                    description=item.description,
                    actor=actor,
                )
                await self._sync_actual_cost(
                    item, actor=actor, previous_actual_qty=0.0,
                )
            else:
                # No prior consumption — just recompute fields.
                item.actual_unit_cost = new_actual_unit_cost
                item.actual_cost = (
                    float(item.actual_quantity or 0) * new_actual_unit_cost
                )
        else:
            await self._sync_actual_cost(
                item, actor=actor, previous_actual_qty=old_actual_qty,
            )

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

        if item.material_id and item.actual_quantity:
            await self._record_inventory_adjustment(
                project=project,
                material_id=item.material_id,
                quantity=-float(item.actual_quantity),
                unit_cost=_effective_unit_cost(item),
                reason="Item deleted — consumption reversed",
                description=item.description,
                actor=actor,
            )

        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="project_items",
            record_id=item.id,
            user_id=actor.id,
            old_data={
                "project_id": str(project_id),
                "category": item.category,
                "description": item.description,
                "actual_cost": float(item.actual_cost or 0),
            },
        )

        await self.projects.delete_item(item)
        await self.recalc_project_totals(project_id)

    # ── Internal helpers ───────────────────────────────

    async def _sync_actual_cost(
        self,
        item: ProjectItem,
        *,
        actor: User | None = None,
        previous_actual_qty: float | None = None,
    ) -> None:
        actual_unit_cost = _effective_unit_cost(item)
        item.actual_unit_cost = actual_unit_cost
        item.actual_cost = float(item.actual_quantity or 0) * actual_unit_cost

        if item.material_id:
            old_qty = previous_actual_qty if previous_actual_qty is not None else 0.0
            new_qty = float(item.actual_quantity or 0)
            delta = new_qty - old_qty
            if abs(delta) > 1e-6:
                project = await self.projects.get(item.project_id)
                if project:
                    await self._record_inventory_adjustment(
                        project=project,
                        material_id=item.material_id,
                        quantity=delta,
                        unit_cost=actual_unit_cost,
                        reason="Project item consumption update",
                        description=item.description,
                        actor=actor,
                    )

    async def _record_inventory_adjustment(
        self,
        *,
        project: Project,
        material_id: UUID,
        quantity: float,
        unit_cost: float,
        reason: str,
        description: str,
        actor: User | None,
    ) -> None:
        if quantity > 0:
            tx_type = TransactionType.CONSUMPTION.value
            qty = quantity
        else:
            tx_type = TransactionType.ADJUSTMENT_IN.value
            qty = -quantity

        tx = InventoryTransaction(
            material_id=material_id,
            transaction_type=tx_type,
            quantity=qty,
            unit_cost=unit_cost,
            reference_type=ReferenceType.PROJECT.value,
            reference_id=project.id,
            reference_note=f"{project.code} — {description[:80]}",
            notes=reason,
            occurred_at=datetime.now(UTC),
            created_by_id=actor.id if actor else None,
        )
        self.db.add(tx)
        await self.db.flush()

    async def recalc_project_totals(self, project_id: UUID) -> Project:
        project = await self._get_project_or_404(project_id)
        items = await self.projects.list_items(project_id)

        totals: dict[str, float] = {
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

        project.estimated_hpp = sum(
            totals[k] for k in totals if k.startswith("estimated_")
        )
        project.actual_hpp = sum(
            totals[k] for k in totals if k.startswith("actual_")
        )

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

    async def create(self, payload: ProjectCreate, *, actor: User) -> Project:
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
        if payload.assigned_lead_id:
            if not await self.db.get(User, payload.assigned_lead_id):
                raise NotFoundError("Assigned lead user not found")

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

    async def update(self, pid: UUID, payload: ProjectUpdate, *, actor: User) -> Project:
        project = await self._get_or_404(pid)
        if project.status in TERMINAL_PROJECT_STATUSES:
            raise ConflictError(f"Cannot edit a {project.status} project")

        if (
            "assigned_lead_id" in payload.model_fields_set
            and payload.assigned_lead_id is not None
        ):
            if not await self.db.get(User, payload.assigned_lead_id):
                raise NotFoundError("Assigned lead user not found")

        for field in payload.model_fields_set:
            setattr(project, field, getattr(payload, field))

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
        if new_status not in PROJECT_STATUSES:
            raise ValidationError(f"status must be one of {PROJECT_STATUSES}")

        # Lock the project to prevent concurrent transitions from both
        # passing the state-machine check.
        project = await self.repo.get_for_update(pid)
        if not project:
            raise NotFoundError("Project not found")
        await self.db.refresh(project, ["items"])

        current = project.status

        allowed = ALLOWED_PROJECT_TRANSITIONS.get(current, frozenset())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot move project from {current} to {new_status}",
                context={
                    "current": current, "target": new_status,
                    "allowed": sorted(allowed),
                },
            )

        # Guard: approval requires a price to approve against.
        if new_status == ProjectStatus.APPROVED.value:
            if project.approved_price is None and project.quoted_price is None:
                raise ConflictError(
                    "Cannot approve a project without a quoted or approved price"
                )

        project.status = new_status

        if new_status == ProjectStatus.APPROVED.value and project.approved_price is None:
            project.approved_price = project.quoted_price

        if new_status == ProjectStatus.DELIVERED.value:
            project.actual_end_date = _today_local()

        if note:
            existing = project.closing_note or ""
            project.closing_note = (
                f"{existing}\n[{current} → {new_status}] {note}".strip()
            )

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="projects",
            record_id=project.id,
            user_id=actor.id,
            old_data={"status": current},
            new_data={"status": new_status, "note": note},
        )

        if new_status == ProjectStatus.APPROVED.value:
            await self._record_approval_snapshot(project, actor=actor)

        if new_status == ProjectStatus.DELIVERED.value:
            await self._record_delivery_snapshot(project, actor=actor)

        return project

    async def _record_approval_snapshot(self, project, *, actor: User) -> None:
        from app.modules.inquiries.repository import InquiryRepository
        from app.modules.pricing.schemas import PricingSnapshotCreate
        from app.modules.pricing.service import PricingService

        hpp = float(project.actual_hpp or project.estimated_hpp or 0)
        if hpp <= 0:
            return

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
                notes=(
                    f"Snapshot at approval. "
                    f"Status transitioned to {ProjectStatus.APPROVED.value}."
                ),
            ),
            actor=actor,
        )

    async def _record_delivery_snapshot(self, project, *, actor: User) -> None:
        """
        Record the final HPP/price at DELIVERED as a *new* snapshot rather
        than mutating the existing approval snapshot — preserves history.
        """
        from app.modules.pricing.schemas import PricingSnapshotCreate
        from app.modules.pricing.service import PricingService

        final_hpp = float(project.actual_hpp or 0)
        if final_hpp <= 0:
            return

        final_price = (
            float(project.approved_price)
            if project.approved_price
            else (float(project.quoted_price) if project.quoted_price else None)
        )

        service_interest = None
        vehicle_category = None
        if project.inquiry_id:
            from app.modules.inquiries.repository import InquiryRepository
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
                hpp_estimate=final_hpp,
                actual_quoted_price=final_price,
                notes=f"Snapshot at delivery ({ProjectStatus.DELIVERED.value}).",
            ),
            actor=actor,
        )

    async def create_from_inquiry(
        self,
        inquiry_id: UUID,
        *,
        actor: User,
        title: str | None = None,
        quoted_price: float | None = None,
        approved_price: float | None = None,
        start_date: Any | None = None,
        target_end_date: Any | None = None,
    ) -> Project:
        from app.modules.inquiries.constants import InquiryStatus
        from app.modules.inquiries.models import Inquiry
        from app.modules.vehicles.models import Vehicle

        # Advisory lock — one project per inquiry, guaranteed under concurrency.
        from sqlalchemy import text as _text
        await self.db.execute(
            _text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"project-from-inquiry:{inquiry_id}"},
        )

        inquiry = await self.db.get(Inquiry, inquiry_id)
        if not inquiry:
            raise NotFoundError("Inquiry not found")

        existing = (
            await self.db.execute(
                select(Project).where(Project.inquiry_id == inquiry_id)
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(
                f"A project already exists for this inquiry: {existing.code}"
            )

        if inquiry.status not in (
            InquiryStatus.APPROVED.value,
            InquiryStatus.CONVERTED.value,
        ):
            raise ConflictError(
                f"Cannot convert an inquiry in status '{inquiry.status}'. "
                f"Only APPROVED inquiries can be converted."
            )

        if not inquiry.customer_id:
            raise ConflictError(
                "This inquiry has no customer linked — cannot create a project."
            )

        if not title:
            parts: list[str] = []
            if inquiry.service_interest:
                parts.append(inquiry.service_interest.replace("_", " ").title())
            if inquiry.vehicle_id:
                v = await self.db.get(Vehicle, inquiry.vehicle_id)
                if v:
                    parts.append(f"{v.brand} {v.model}")
            title = " — ".join(parts) if parts else f"Project from {inquiry.code}"

        project = Project(
            code=await self.repo.next_code(),
            title=title,
            description=inquiry.description,
            inquiry_id=inquiry.id,
            customer_id=inquiry.customer_id,
            vehicle_id=inquiry.vehicle_id,
            status=ProjectStatus.ESTIMATING.value,
            quoted_price=quoted_price,
            approved_price=approved_price,
            start_date=start_date,
            target_end_date=target_end_date,
            internal_notes=(
                f"Auto-created from inquiry {inquiry.code}.\n"
                f"Service: {inquiry.service_interest or '—'}\n"
                f"Color: {inquiry.color_preference or '—'}\n"
                f"Finish: {inquiry.finish_preference or '—'}"
            ),
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
                "inquiry_id": str(inquiry.id),
                "inquiry_code": inquiry.code,
                "customer_id": str(inquiry.customer_id),
                "vehicle_id": str(inquiry.vehicle_id) if inquiry.vehicle_id else None,
            },
        )

        log.info(
            "project_created_from_inquiry",
            inquiry_code=inquiry.code,
            project_code=project.code,
        )
        return project

    async def _get_or_404(self, pid: UUID) -> Project:
        p = await self.repo.get(pid)
        if not p:
            raise NotFoundError("Project not found")
        return p