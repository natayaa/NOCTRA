from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Path, Query

from app.core.config import settings
from app.core.constants import AuditAction, PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.core.pagination import Page, PageParams, page_params, paginate
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import (
    AuditCatalog,
    AuditLogDetail,
    AuditLogItem,
)
from app.modules.auth.dependencies import require_permission

router = APIRouter(prefix="/audit", tags=["audit"])

_APP_TZ = ZoneInfo(settings.APP_TIMEZONE)
_KNOWN_ACTIONS = {a.value for a in AuditAction}


def _to_utc(dt: datetime | None) -> datetime | None:
    """Normalize incoming datetimes to UTC.

    Naive values are interpreted in the app's configured timezone
    (`APP_TIMEZONE`), matching how a browser date picker means "Jan 1
    local" and how the analytics module resolves period presets.
    Explicitly-tagged values (`Z`, `+07:00`, etc.) are honoured.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_APP_TZ).astimezone(UTC)
    return dt.astimezone(UTC)


@router.get("/catalog", response_model=AuditCatalog)
async def catalog(
    db: DbSession,
    _=Depends(require_permission(PermissionCode.AUDIT_READ)),
) -> AuditCatalog:
    """Filter options for the audit UI: actions + observed table names."""
    repo = AuditRepository(db)
    return AuditCatalog(
        actions=[a.value for a in AuditAction],
        tables=await repo.distinct_tables(),
    )


@router.get("", response_model=Page[AuditLogItem])
async def list_audit(
    db: DbSession,
    params: PageParams = Depends(page_params),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None, max_length=32),
    table_name: str | None = Query(None, max_length=100),
    record_id: str | None = Query(None, max_length=64),
    since: datetime | None = Query(None, description="Inclusive lower bound"),
    until: datetime | None = Query(None, description="Exclusive upper bound"),
    _=Depends(require_permission(PermissionCode.AUDIT_READ)),
) -> Page[AuditLogItem]:
    # Reject unknown actions early — an empty page in response to a typo
    # is confusing for API clients that bypass /audit/catalog.
    if action is not None and action not in _KNOWN_ACTIONS:
        raise ValidationError(
            f"Unknown action {action!r}. "
            f"Valid: {', '.join(sorted(_KNOWN_ACTIONS))}"
        )

    since_utc = _to_utc(since)
    until_utc = _to_utc(until)
    if since_utc is not None and until_utc is not None and since_utc >= until_utc:
        raise ValidationError("`since` must be strictly before `until`")

    repo = AuditRepository(db)
    stmt = repo.query(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        since=since_utc,
        until=until_utc,
    )
    rows, meta = await paginate(db, stmt, params)

    # Batch-fetch user emails (1 query, not N+1)
    user_ids = {r.user_id for r in rows if r.user_id}
    emails = await repo.user_emails(user_ids)

    items = [
        AuditLogItem.model_validate(r).model_copy(
            update={"user_email": emails.get(r.user_id) if r.user_id else None}
        )
        for r in rows
    ]
    return Page[AuditLogItem](items=items, meta=meta)


@router.get("/{audit_id}", response_model=AuditLogDetail)
async def get_audit(
    db: DbSession,
    audit_id: UUID = Path(...),
    _=Depends(require_permission(PermissionCode.AUDIT_READ)),
) -> AuditLogDetail:
    repo = AuditRepository(db)
    row = await repo.get(audit_id)
    if row is None:
        raise NotFoundError("Audit log not found")

    emails = await repo.user_emails({row.user_id} if row.user_id else set())
    item = AuditLogDetail.model_validate(row)
    if row.user_id:
        item = item.model_copy(update={"user_email": emails.get(row.user_id)})
    return item