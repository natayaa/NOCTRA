"""Read/write helpers for the inquiries module."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inquiries.constants import TERMINAL_STATUSES
from app.modules.inquiries.models import Inquiry, InquiryPhoto


class InquiryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Reads ─────────────────────────────────────────
    async def get(self, inquiry_id: UUID) -> Inquiry | None:
        return await self.db.get(Inquiry, inquiry_id)

    async def get_by_code(self, code: str) -> Inquiry | None:
        stmt = select(Inquiry).where(Inquiry.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        assigned_to_id: UUID | None = None,
        customer_id: UUID | None = None,
        source: str | None = None,
        color_family: str | None = None,
        finish_preference: str | None = None,
        only_open: bool = False,
    ) -> Select:
        stmt = select(Inquiry).order_by(Inquiry.created_at.desc())
        conds = []

        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Inquiry.code.ilike(like),
                    Inquiry.description.ilike(like),
                    Inquiry.notes.ilike(like),
                )
            )
        if status:
            conds.append(Inquiry.status == status)
        if assigned_to_id is not None:
            conds.append(Inquiry.assigned_to_id == assigned_to_id)
        if customer_id is not None:
            conds.append(Inquiry.customer_id == customer_id)
        if source:
            conds.append(Inquiry.source == source)
        if color_family:
            conds.append(Inquiry.color_family == color_family)
        if finish_preference:
            conds.append(Inquiry.finish_preference == finish_preference)
        if only_open:
            conds.append(Inquiry.status.not_in(TERMINAL_STATUSES))

        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def list_photos(self, inquiry_id: UUID) -> list[InquiryPhoto]:
        stmt = (
            select(InquiryPhoto)
            .where(InquiryPhoto.inquiry_id == inquiry_id)
            .order_by(InquiryPhoto.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def next_code(self) -> str:
        """Generate NOCTRA-I-YYYY-NNNNNN. Annual reset."""
        year = datetime.now(UTC).year
        prefix = f"NOCTRA-I-{year}-"
        stmt = (
            select(Inquiry.code)
            .where(Inquiry.code.like(f"{prefix}%"))
            .order_by(Inquiry.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        next_n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{next_n:06d}"

    # ── Writes ────────────────────────────────────────
    async def add(self, inquiry: Inquiry) -> Inquiry:
        self.db.add(inquiry)
        await self.db.flush()
        return inquiry

    async def add_photo(self, photo: InquiryPhoto) -> InquiryPhoto:
        self.db.add(photo)
        await self.db.flush()
        return photo