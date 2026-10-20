"""Read/write helpers for the inquiries module."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.inquiries.constants import (
    NON_TERMINAL_STATUSES,
    OPEN_STATUSES,
    today_local,
)
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
        sort: str = "created_desc",
    ) -> Select:
        # `noload` prevents the selectin eager loader for photos from
        # firing on list queries — photos are only needed in detail views.
        stmt = select(Inquiry).options(noload(Inquiry.photos))
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
            # Consistent with stats: everything except CONVERTED / LOST
            # (i.e. includes APPROVED, which still needs action).
            conds.append(Inquiry.status.in_(NON_TERMINAL_STATUSES))

        if conds:
            stmt = stmt.where(and_(*conds))

        # Stable secondary sort on id prevents pagination drift when
        # created_at timestamps collide (e.g. bulk imports).
        if sort == "created_asc":
            stmt = stmt.order_by(Inquiry.created_at.asc(), Inquiry.id.asc())
        elif sort == "updated_desc":
            stmt = stmt.order_by(Inquiry.updated_at.desc(), Inquiry.id.asc())
        elif sort == "follow_up_asc":
            stmt = stmt.order_by(
                Inquiry.follow_up_date.asc().nulls_last(), Inquiry.id.asc()
            )
        elif sort == "status_asc":
            stmt = stmt.order_by(
                Inquiry.status.asc(), Inquiry.created_at.desc(), Inquiry.id.asc()
            )
        else:  # created_desc
            stmt = stmt.order_by(Inquiry.created_at.desc(), Inquiry.id.asc())

        return stmt

    async def list_photos(self, inquiry_id: UUID) -> list[InquiryPhoto]:
        stmt = (
            select(InquiryPhoto)
            .where(InquiryPhoto.inquiry_id == inquiry_id)
            .order_by(
                InquiryPhoto.is_primary.desc(),
                InquiryPhoto.created_at.desc(),
            )
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def photo_count(self, inquiry_id: UUID) -> int:
        stmt = (
            select(func.count(InquiryPhoto.id))
            .where(InquiryPhoto.inquiry_id == inquiry_id)
        )
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    async def stats(self, *, assigned_to_id: UUID | None = None) -> dict[str, int]:
        """Return counts per status + overdue follow-ups."""
        base = select(Inquiry.status, func.count(Inquiry.id)).group_by(Inquiry.status)
        if assigned_to_id is not None:
            base = base.where(Inquiry.assigned_to_id == assigned_to_id)
        rows = (await self.db.execute(base)).all()
        by_status = {status: count for status, count in rows}

        overdue_stmt = select(func.count(Inquiry.id)).where(
            Inquiry.follow_up_date.is_not(None),
            Inquiry.follow_up_date < today_local(),
            Inquiry.status.in_(NON_TERMINAL_STATUSES),
        )
        if assigned_to_id is not None:
            overdue_stmt = overdue_stmt.where(Inquiry.assigned_to_id == assigned_to_id)
        overdue = (await self.db.execute(overdue_stmt)).scalar_one()

        return {
            "total": sum(by_status.values()),
            # `open` matches the `only_open=true` filter exactly.
            "open": sum(by_status.get(s, 0) for s in NON_TERMINAL_STATUSES),
            "overdue": overdue,
            # Pre-approval subset for KPI widgets.
            "pre_approval": sum(by_status.get(s, 0) for s in OPEN_STATUSES),
            **{f"status_{k}": v for k, v in by_status.items()},
        }

    async def next_code(self) -> str:
        """
        Generate NOCTRA-I-YYYY-NNNNNN under an advisory lock.
        Annual reset; the lock key includes the year to avoid serialising
        across the year boundary.
        """
        year = datetime.now(UTC).year
        prefix = f"NOCTRA-I-{year}-"

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": prefix},
        )

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

    async def delete_photo(self, photo: InquiryPhoto) -> None:
        await self.db.delete(photo)
        await self.db.flush()