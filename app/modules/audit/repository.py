from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def query(
        self,
        *,
        user_id: UUID | None = None,
        action: str | None = None,
        table_name: str | None = None,
        since: datetime | None = None,
    ):
        conditions = []
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if action is not None:
            conditions.append(AuditLog.action == action)
        if table_name is not None:
            conditions.append(AuditLog.table_name == table_name)
        if since is not None:
            conditions.append(AuditLog.created_at >= since)

        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt