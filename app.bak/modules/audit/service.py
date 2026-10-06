from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.audit.models import AuditLog


class AuditService:
    """
    Write-side audit. Add-only; never updates or deletes.
    Callers are responsible for committing the session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        action: str,
        table_name: str,
        record_id: str | UUID,
        user_id: UUID | None = None,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.db.add(
            AuditLog(
                action=action,
                table_name=table_name,
                record_id=str(record_id),
                user_id=user_id,
                old_data=old_data,
                new_data=new_data,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )