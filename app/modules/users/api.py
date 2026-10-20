"""User REST endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    AdminPasswordReset,
    SelfPasswordChange,
    UserCreate,
    UserDetail,
    UserListItem,
    UserUpdate,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _detail(user) -> UserDetail:
    detail = UserDetail.model_validate(user)
    detail.roles = [r.name for r in user.roles]
    return detail


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_model=Page[UserListItem])
async def list_users(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(None),
    role_name: str | None = Query(None, max_length=50),
    _=Depends(require_permission(PermissionCode.USER_READ)),
) -> Page[UserListItem]:
    stmt = UserRepository(db).query(
        q=q, is_active=is_active, role_name=role_name,
    )
    rows, meta = await paginate(db, stmt, params)
    return Page[UserListItem](
        items=[UserListItem.model_validate(r) for r in rows],
        meta=meta,
    )


# ════════════════════════════════════════════════════════════════
# CREATE / READ / UPDATE
# ════════════════════════════════════════════════════════════════

@router.post("", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_CREATE)),
) -> UserDetail:
    user = await UserService(db).create(payload, actor=actor)
    return _detail(user)


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.USER_READ)),
) -> UserDetail:
    user = await UserRepository(db).get(user_id)
    if not user:
        raise NotFoundError("User not found")
    return _detail(user)


@router.patch("/{user_id}", response_model=UserDetail)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_UPDATE)),
) -> UserDetail:
    user = await UserService(db).update(user_id, payload, actor=actor)
    return _detail(user)


# ════════════════════════════════════════════════════════════════
# PASSWORD — self vs admin
# ════════════════════════════════════════════════════════════════

@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    payload: SelfPasswordChange,
    db: DbSession,
    actor: CurrentUser,
) -> None:
    """
    Self-service password change. Requires the CURRENT password. No
    permission code needed beyond being authenticated — this is the user
    changing their own password, period.
    """
    await UserService(db).change_own_password(actor.id, payload, actor=actor)


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_reset_password(
    user_id: UUID,
    payload: AdminPasswordReset,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_UPDATE)),
) -> None:
    """
    Admin-driven password reset. No old_password required — this endpoint
    is guarded by USER_UPDATE. Superusers can additionally reset other
    superusers' passwords.
    """
    await UserService(db).reset_password(user_id, payload, actor=actor)


# ════════════════════════════════════════════════════════════════
# DEACTIVATE / REACTIVATE
# ════════════════════════════════════════════════════════════════

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_DELETE)),
) -> None:
    await UserService(db).deactivate(user_id, actor=actor)


@router.post("/{user_id}/reactivate", response_model=UserDetail)
async def reactivate_user(
    user_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_UPDATE)),
) -> UserDetail:
    user = await UserService(db).reactivate(user_id, actor=actor)
    return _detail(user)