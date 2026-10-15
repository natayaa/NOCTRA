"""Business rules for the inquiries module."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.customers.repository import CustomerRepository
from app.modules.inquiries.constants import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATUSES,
    InquiryStatus,
)
from app.modules.inquiries.models import Inquiry, InquiryPhoto
from app.modules.inquiries.repository import InquiryRepository
from app.modules.inquiries.schemas import (
    InquiryCreate,
    InquiryPhotoIn,
    InquiryStatusChange,
    InquiryUpdate,
)
from app.modules.vehicles.repository import VehicleRepository


# Fields whose changes should be tracked in the audit snapshot
_SNAPSHOT_FIELDS = (
    "status", "service_interest", "description",
    "color_preference", "color_family", "finish_preference",
    "has_custom_graphics", "budget_range",
    "desired_date", "follow_up_date",
    "notes", "closing_note", "preferences",
)


class InquiryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InquiryRepository(db)
        self.customers = CustomerRepository(db)
        self.vehicles = VehicleRepository(db)
        self.audit = AuditService(db)

    # ── Create ────────────────────────────────────────
    async def create(self, payload: InquiryCreate, *, actor: User | None = None) -> Inquiry:
        if payload.customer_id and not await self.customers.get(payload.customer_id):
            raise NotFoundError("Customer not found")
        if payload.vehicle_id and not await self.vehicles.get(payload.vehicle_id):
            raise NotFoundError("Vehicle not found")

        inquiry = Inquiry(
            code=await self.repo.next_code(),
            customer_id=payload.customer_id,
            vehicle_id=payload.vehicle_id,
            service_interest=payload.service_interest,
            description=payload.description.strip(),
            color_preference=payload.color_preference,
            color_family=payload.color_family,
            finish_preference=payload.finish_preference,
            has_custom_graphics=payload.has_custom_graphics or False,
            preferences=payload.preferences,
            status=InquiryStatus.NEW.value,
            source=payload.source,
            budget_range=payload.budget_range,
            desired_date=payload.desired_date,
            follow_up_date=payload.follow_up_date,
            notes=payload.notes,
        )
        await self.repo.add(inquiry)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="inquiries",
            record_id=inquiry.id,
            user_id=actor.id if actor else None,
            new_data={"code": inquiry.code, "status": inquiry.status, "source": inquiry.source},
        )
        return inquiry

    # ── Update ────────────────────────────────────────
    async def update(self, inquiry_id: UUID, payload: InquiryUpdate, *, actor: User) -> Inquiry:
        inquiry = await self._get_or_404(inquiry_id)

        if inquiry.status in TERMINAL_STATUSES:
            raise ConflictError(f"Cannot edit inquiry in terminal state {inquiry.status}")

        before = self._snapshot(inquiry)
        fields = payload.model_fields_set

        if "customer_id" in fields:
            if payload.customer_id and not await self.customers.get(payload.customer_id):
                raise NotFoundError("Customer not found")
            inquiry.customer_id = payload.customer_id

        if "vehicle_id" in fields:
            if payload.vehicle_id and not await self.vehicles.get(payload.vehicle_id):
                raise NotFoundError("Vehicle not found")
            inquiry.vehicle_id = payload.vehicle_id

        for field in (
            "service_interest", "description", "color_preference",
            "color_family", "finish_preference", "has_custom_graphics",
            "preferences", "budget_range", "desired_date",
            "follow_up_date", "notes",
        ):
            if field in fields:
                setattr(inquiry, field, getattr(payload, field))

        await self.db.flush()

        after = self._snapshot(inquiry)
        if before != after:
            await self.audit.log(
                action=AuditAction.UPDATE,
                table_name="inquiries",
                record_id=inquiry.id,
                user_id=actor.id,
                old_data=before,
                new_data=after,
            )
        return inquiry

    # ── Assign ────────────────────────────────────────
    async def assign(self, inquiry_id: UUID, assignee_id: UUID | None, *, actor: User) -> Inquiry:
        inquiry = await self._get_or_404(inquiry_id)
        if inquiry.status in TERMINAL_STATUSES:
            raise ConflictError("Cannot reassign a closed inquiry")

        before = inquiry.assigned_to_id
        inquiry.assigned_to_id = assignee_id
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.ASSIGN,
            table_name="inquiries",
            record_id=inquiry.id,
            user_id=actor.id,
            old_data={"assigned_to_id": str(before) if before else None},
            new_data={"assigned_to_id": str(assignee_id) if assignee_id else None},
        )
        return inquiry

    # ── Status change ─────────────────────────────────
    async def change_status(
        self,
        inquiry_id: UUID,
        payload: InquiryStatusChange,
        *,
        actor: User,
    ) -> Inquiry:
        inquiry = await self._get_or_404(inquiry_id)
        current, target = inquiry.status, payload.status

        allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise ConflictError(
                f"Cannot move inquiry from {current} to {target}",
                context={"current": current, "target": target, "allowed": sorted(allowed)},
            )

        if target == InquiryStatus.LOST.value and not payload.closing_note:
            raise ValidationError("A closing note is required when marking an inquiry as LOST")

        # CONVERTED delegates to the conversion workflow
        if target == InquiryStatus.CONVERTED.value:
            inquiry, _ = await self.convert_to_project(inquiry_id, actor=actor)
            if payload.closing_note:
                inquiry.closing_note = payload.closing_note
                await self.db.flush()
            return inquiry

        inquiry.status = target
        if current == InquiryStatus.NEW.value:
            inquiry.last_contacted_at = datetime.now(UTC)
        if "closing_note" in payload.model_fields_set:
            inquiry.closing_note = payload.closing_note

        await self.db.flush()
        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="inquiries",
            record_id=inquiry.id,
            user_id=actor.id,
            old_data={"status": current},
            new_data={"status": target},
        )
        return inquiry

    async def mark_contacted(self, inquiry_id: UUID, *, actor: User) -> Inquiry:
        # Guard: only NEW → CONTACTED via this shortcut
        inquiry = await self._get_or_404(inquiry_id)
        if inquiry.status != InquiryStatus.NEW.value:
            raise ConflictError(
                f"mark_contacted only valid from NEW (current: {inquiry.status})"
            )
        return await self.change_status(
            inquiry_id,
            InquiryStatusChange(status=InquiryStatus.CONTACTED.value),
            actor=actor,
        )

    # ── Photos ────────────────────────────────────────
    async def add_photo(self, inquiry_id: UUID, payload: InquiryPhotoIn, *, actor: User) -> InquiryPhoto:
        inquiry = await self._get_or_404(inquiry_id)

        if payload.is_primary:
            for existing in await self.repo.list_photos(inquiry_id):
                existing.is_primary = False

        photo = InquiryPhoto(
            inquiry_id=inquiry.id,
            file_path=payload.file_path,
            file_name=payload.file_name,
            caption=payload.caption,
            is_primary=payload.is_primary,
        )
        await self.repo.add_photo(photo)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="inquiry_photos",
            record_id=photo.id,
            user_id=actor.id,
            new_data={"inquiry_id": str(inquiry.id), "file_path": photo.file_path},
        )
        return photo

    async def delete_photo(self, photo_id: UUID, *, actor: User) -> None:
        photo = await self.db.get(InquiryPhoto, photo_id)
        if not photo:
            raise NotFoundError("Photo not found")
        inquiry_id = photo.inquiry_id
        await self.repo.delete_photo(photo)
        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="inquiry_photos",
            record_id=photo_id,
            user_id=actor.id,
            old_data={"inquiry_id": str(inquiry_id), "file_path": photo.file_path},
        )

    # ── Convert to project ────────────────────────────
    async def convert_to_project(
        self,
        inquiry_id: UUID,
        *,
        actor: User,
        quoted_price: float | None = None,
        approved_price: float | None = None,
    ) -> tuple[Inquiry, "Project"]:
        from app.modules.projects.service import ProjectService

        inquiry = await self._get_or_404(inquiry_id)
        if inquiry.status != InquiryStatus.APPROVED.value:
            raise ConflictError(
                f"Cannot convert an inquiry in status '{inquiry.status}'. Move it to APPROVED first."
            )

        project = await ProjectService(self.db).create_from_inquiry(
            inquiry_id,
            actor=actor,
            quoted_price=quoted_price,
            approved_price=approved_price,
        )

        inquiry.status = InquiryStatus.CONVERTED.value
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="inquiries",
            record_id=inquiry.id,
            user_id=actor.id,
            old_data={"status": InquiryStatus.APPROVED.value},
            new_data={
                "status": InquiryStatus.CONVERTED.value,
                "project_id": str(project.id),
                "project_code": project.code,
            },
        )
        log.info("inquiry_converted", inquiry_code=inquiry.code, project_code=project.code)
        return inquiry, project

    # ── Timeline ──────────────────────────────────────
    async def get_timeline(self, inquiry_id: UUID, limit: int = 30) -> list[dict]:
        """Best-effort activity feed from the audit log."""
        try:
            from app.modules.audit.models import AuditLog  # type: ignore
        except Exception:  # audit model not exposed publicly
            return []
        from sqlalchemy import select
        stmt = (
            select(AuditLog)
            .where(AuditLog.table_name == "inquiries", AuditLog.record_id == str(inquiry_id))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            {
                "action": getattr(r, "action", None),
                "user_id": getattr(r, "user_id", None),
                "old_data": getattr(r, "old_data", None),
                "new_data": getattr(r, "new_data", None),
                "created_at": getattr(r, "created_at", None),
            }
            for r in rows
        ]

    # ── Helpers ───────────────────────────────────────
    async def _get_or_404(self, inquiry_id: UUID) -> Inquiry:
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError("Inquiry not found")
        return inquiry

    @staticmethod
    def _snapshot(i: Inquiry) -> dict:
        snap: dict = {
            "status": i.status,
            "assigned_to_id": str(i.assigned_to_id) if i.assigned_to_id else None,
            "customer_id": str(i.customer_id) if i.customer_id else None,
            "vehicle_id": str(i.vehicle_id) if i.vehicle_id else None,
        }
        for f in _SNAPSHOT_FIELDS:
            v = getattr(i, f, None)
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            snap[f] = v
        return snap