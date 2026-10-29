"""Read/write helpers for the inquiries module."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
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

    async def recent_duplicate(
        self, *, customer_id: UUID, description: str, within_minutes: int
    ) -> Inquiry | None:
        """Same customer, same text, recent — almost always a double-submit.

        Only exact description matches count. Two different jobs for one
        customer rarely share their request text verbatim, and a false
        merge would silently swallow a real inquiry, so the check is
        deliberately narrow.
        """
        if within_minutes <= 0:
            return None
        cutoff = datetime.now(UTC) - timedelta(minutes=within_minutes)
        stmt = (
            select(Inquiry)
            .where(
                Inquiry.customer_id == customer_id,
                Inquiry.description == description,
                Inquiry.created_at >= cutoff,
            )
            .order_by(Inquiry.created_at.desc())
            .limit(1)
        )
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
            conds.append(Inquiry.status.in_(NON_TERMINAL_STATUSES))

        if conds:
            stmt = stmt.where(and_(*conds))

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
            "open": sum(by_status.get(s, 0) for s in NON_TERMINAL_STATUSES),
            "overdue": overdue,
            "pre_approval": sum(by_status.get(s, 0) for s in OPEN_STATUSES),
            **{f"status_{k}": v for k, v in by_status.items()},
        }

    async def next_code(self) -> str:
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

    # ── Advisory locks ────────────────────────────────
    async def lock_for_mutation(self, inquiry_id: UUID) -> None:
        """Serialize workflow mutations (assign, status change, convert).

        A single key is used for all workflow mutations so that a concurrent
        `assign` and `change_status(LOST)` cannot both pass their
        `TERMINAL_STATUSES` check — without this lock, an inquiry could end
        up terminal *and* still carry an assignee.
        """
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"inquiry-mutate:{inquiry_id}"},
        )

    async def lock_for_photo(self, inquiry_id: UUID) -> None:
        """Serialize photo uploads so the MAX_PHOTOS check is atomic.

        Separate key from `lock_for_mutation` — photo uploads should not be
        blocked by (or block) workflow transitions.
        """
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"inquiry-photo:{inquiry_id}"},
        )

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