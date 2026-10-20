"""
Write-side audit. Append-only; never updates or deletes.

Sensitive values (passwords, tokens, secrets) are redacted before the
record is written. Callers are responsible for committing the session.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.modules.audit.models import AuditLog

# Exact-match sensitive keys (case-insensitive).
_SENSITIVE_EXACT: set[str] = {
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token",
    "secret", "api_key", "authorization",
    "csrf", "csrf_token",
    "password_hash", "hashed_password",
}
# Suffix-matched sensitive keys — catches `old_password`, `user_token`, ...
_SENSITIVE_SUFFIXES: tuple[str, ...] = (
    "_password", "_token", "_secret", "_api_key", "_csrf_token",
)
_MAX_REDACT_DEPTH = 5


def _is_sensitive_key(k: str) -> bool:
    kl = str(k).lower()
    return kl in _SENSITIVE_EXACT or kl.endswith(_SENSITIVE_SUFFIXES)


def _redact(obj: Any, depth: int = 0) -> Any:
    """Recursively replace sensitive values with '***'."""
    if depth > _MAX_REDACT_DEPTH:
        return obj
    if isinstance(obj, dict):
        return {
            k: ("***" if _is_sensitive_key(k) else _redact(v, depth + 1))
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return type(obj)(_redact(v, depth + 1) for v in obj)
    return obj


class AuditService:
    """
    Write-side audit. Append-only; never updates or deletes.
    Callers are responsible for committing the session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        action: AuditAction | str,
        table_name: str,
        record_id: str | UUID,
        user_id: UUID | None = None,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        flush: bool = False,
    ) -> AuditLog:
        """
        Record one audit entry. Returns the ORM object so callers can
        read `id` / `created_at` after flush/commit.

        `flush=True` makes the row queryable within the current
        transaction (useful when the audit is read back mid-request).
        """
        action_value = (
            action.value if isinstance(action, AuditAction) else str(action)
        )

        entry = AuditLog(
            action=action_value,
            table_name=table_name,
            record_id=str(record_id),
            user_id=user_id,
            old_data=_redact(old_data) if old_data is not None else None,
            new_data=_redact(new_data) if new_data is not None else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        if flush:
            await self.db.flush()
        return entry