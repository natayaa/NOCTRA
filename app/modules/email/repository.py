"""Read/write helpers for the email module."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.email.models import EmailLog


class EmailLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, log_id: UUID) -> EmailLog | None:
        return await self.db.get(EmailLog, log_id)

    def query(
        self,
        *,
        template: str | None = None,
        status: str | None = None,
        related_type: str | None = None,
        related_id: UUID | None = None,
        to_email: str | None = None,
    ) -> Select:
        stmt = select(EmailLog).order_by(EmailLog.created_at.desc())
        conds = []
        if template:
            conds.append(EmailLog.template == template)
        if status:
            conds.append(EmailLog.status == status)
        if related_type:
            conds.append(EmailLog.related_type == related_type)
        if related_id:
            conds.append(EmailLog.related_id == related_id)
        if to_email:
            conds.append(EmailLog.to_email == to_email)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def add(self, log: EmailLog) -> EmailLog:
        self.db.add(log)
        await self.db.flush()
        return log