from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.pagination import Page, paginate, page_params, PageParams
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import AuditLogItem
from app.modules.auth.dependencies import require_permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[AuditLogItem])
async def list_audit(
    db: DbSession,
    params: PageParams = Depends(page_params),
    user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    table_name: str | None = Query(None),
    since: datetime | None = Query(None),
    _=Depends(require_permission(PermissionCode.AUDIT_READ)),
) -> Page[AuditLogItem]:
    stmt = AuditRepository(db).query(
        user_id=user_id,
        action=action,
        table_name=table_name,
        since=since,
    )
    rows, meta = await paginate(db, stmt, params)
    return Page[AuditLogItem](items=[AuditLogItem.model_validate(r) for r in rows], meta=meta)