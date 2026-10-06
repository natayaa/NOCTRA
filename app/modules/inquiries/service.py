"""Business rules for the inquiries module.

Enforces:
- Allowed status transitions only.
- Auto-set `last_contacted_at` when moving out of NEW.
- Audit logging on every mutation.
- Assignment validation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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


class InquiryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InquiryRepository(db)
        self.customers = CustomerRepository(db)
        self.vehicles = VehicleRepository(db)
        self.audit = AuditService(db)

    # ── Create ────────────────────────────────────────
    async def create(
        self, payload: InquiryCreate, *, actor: User | None = None
    ) -> Inquiry:
        if payload.customer_id:
            if not await self.customers.get(payload.customer_id):
                raise NotFoundError("Customer not found")
        if payload.vehicle_id:
            if not await self.vehicles.get(payload.vehicle_id):
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
            has_custom_graphics=payload.has_custom_graphics,
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
            new_data={
                "code": inquiry.code,
                "status": inquiry.status,
                "source": inquiry.source,
            },
        )

        await self.db.refresh(inquiry, ["photos"])
        return inquiry

    # ── Update ────────────────────────────────────────
    async def update(
        self, inquiry_id: UUID, payload: InquiryUpdate, *, actor: User
    ) -> Inquiry:
        inquiry = await self._get_or_404(inquiry_id)

        if inquiry.status in TERMINAL_STATUSES:
            raise ConflictError(
                f"Cannot edit inquiry in terminal state {inquiry.status}"
            )

        before = self._snapshot(inquiry)

        if payload.customer_id is not None:
            if payload.customer_id and not await self.customers.get(payload.customer_id):
                raise NotFoundError("Customer not found")
            inquiry.customer_id = payload.customer_id

        if payload.vehicle_id is not None:
            if payload.vehicle_id and not await self.vehicles.get(payload.vehicle_id):
                raise NotFoundError("Vehicle not found")
            inquiry.vehicle_id = payload.vehicle_id

        for field in (
            "service_interest",
            "description",
            "color_preference",
            "color_family",
            "finish_preference",
            "has_custom_graphics",
            "preferences",
            "budget_range",
            "desired_date",
            "follow_up_date",
            "notes",
        ):
            value = getattr(payload, field, None)
            if value is not None:
                setattr(inquiry, field, value)

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="inquiries",
            record_id=inquiry.id,
            user_id=actor.id,
            old_data=before,
            new_data=self._snapshot(inquiry),
        )
        return inquiry

    # ── Assignment ────────────────────────────────────
    async def assign(
        self, inquiry_id: UUID, assignee_id: UUID | None, *, actor: User
    ) -> Inquiry:
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

    # ── Status transition ─────────────────────────────
    async def change_status(
        self,
        inquiry_id: UUID,
        payload: InquiryStatusChange,
        *,
        actor: User,
    ) -> Inquiry:
        inquiry = await self._get_or_404(inquiry_id)

        current = inquiry.status
        target = payload.status

        allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise ConflictError(
                f"Cannot move inquiry from {current} to {target}",
                context={"current": current, "target": target, "allowed": sorted(allowed)},
            )

        if target == InquiryStatus.LOST.value and not payload.closing_note:
            raise ValidationError(
                "A closing note is required when marking an inquiry as LOST"
            )

        before = current
        inquiry.status = target

        # Auto-set last_contacted_at when leaving NEW
        if current == InquiryStatus.NEW.value and target != InquiryStatus.NEW.value:
            inquiry.last_contacted_at = datetime.now(UTC)

        if payload.closing_note:
            inquiry.closing_note = payload.closing_note

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="inquiries",
            record_id=inquiry.id,
            user_id=actor.id,
            old_data={"status": before},
            new_data={"status": target},
        )
        return inquiry

    # ── Mark contacted (shortcut) ─────────────────────
    async def mark_contacted(self, inquiry_id: UUID, *, actor: User) -> Inquiry:
        return await self.change_status(
            inquiry_id,
            InquiryStatusChange(status=InquiryStatus.CONTACTED.value),
            actor=actor,
        )

    # ── Photos ────────────────────────────────────────
    async def add_photo(
        self, inquiry_id: UUID, payload: InquiryPhotoIn, *, actor: User
    ) -> InquiryPhoto:
        inquiry = await self._get_or_404(inquiry_id)

        if payload.is_primary:
            # Unset any previous primary
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

    # ── Helpers ───────────────────────────────────────
    async def _get_or_404(self, inquiry_id: UUID) -> Inquiry:
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError("Inquiry not found")
        return inquiry

    @staticmethod
    def _snapshot(i: Inquiry) -> dict:
        return {
            "status": i.status,
            "assigned_to_id": str(i.assigned_to_id) if i.assigned_to_id else None,
            "service_interest": i.service_interest,
            "color_family": i.color_family,
            "finish_preference": i.finish_preference,
            "has_custom_graphics": i.has_custom_graphics,
        }