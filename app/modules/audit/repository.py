from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog

# Adjust if your User model uses `name`/`username` instead of `email`.
from app.modules.auth.models import User


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def query(
        self,
        *,
        user_id: UUID | None = None,
        action: str | None = None,
        table_name: str | None = None,
        record_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ):
        conditions = []
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if action is not None:
            conditions.append(AuditLog.action == action)
        if table_name is not None:
            conditions.append(AuditLog.table_name == table_name)
        if record_id is not None:
            conditions.append(AuditLog.record_id == record_id)
        if since is not None:
            conditions.append(AuditLog.created_at >= since)
        if until is not None:
            conditions.append(AuditLog.created_at < until)

        # Stable secondary sort on `id` prevents pagination drift when
        # multiple rows share the same created_at timestamp.
        stmt = select(AuditLog).order_by(
            AuditLog.created_at.desc(), AuditLog.id.desc()
        )
        if conditions:
            stmt = stmt.where(*conditions)
        return stmt

    async def get(self, audit_id: UUID) -> AuditLog | None:
        return await self.db.get(AuditLog, audit_id)

    async def user_emails(self, user_ids: set[UUID]) -> dict[UUID, str]:
        """Batch-fetch user emails to enrich list/detail responses."""
        if not user_ids:
            return {}
        stmt = select(User.id, User.email).where(User.id.in_(user_ids))
        rows = (await self.db.execute(stmt)).all()
        return {uid: email for uid, email in rows}

    async def distinct_tables(self) -> list[str]:
        """All table names that appear in audit logs — for filter dropdowns."""
        stmt = (
            select(AuditLog.table_name)
            .distinct()
            .order_by(AuditLog.table_name)
        )
        return list((await self.db.execute(stmt)).scalars().all())