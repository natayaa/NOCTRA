from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.pagination import Page, PageMeta, paginate, page_params, PageParams
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserCreate,
    UserDetail,
    UserListItem,
    UserPasswordChange,
    UserUpdate,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserListItem])
async def list_users(
    db: DbSession,
    params: PageParams = Depends(page_params),
    _=Depends(require_permission(PermissionCode.USER_READ)),
) -> Page[UserListItem]:
    rows, meta = await paginate(db, UserRepository(db).query(), params)
    return Page[UserListItem](
        items=[UserListItem.model_validate(r) for r in rows],
        meta=meta,
    )


@router.post("", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_CREATE)),
) -> UserDetail:
    user = await UserService(db).create(payload, actor=actor)
    detail = UserDetail.model_validate(user)
    detail.roles = [r.name for r in user.roles]
    return detail


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.USER_READ)),
) -> UserDetail:
    user = await UserRepository(db).get(user_id)
    if not user:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("User not found")
    detail = UserDetail.model_validate(user)
    detail.roles = [r.name for r in user.roles]
    return detail


@router.patch("/{user_id}", response_model=UserDetail)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_UPDATE)),
) -> UserDetail:
    user = await UserService(db).update(user_id, payload, actor=actor)
    detail = UserDetail.model_validate(user)
    detail.roles = [r.name for r in user.roles]
    return detail


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    user_id: UUID,
    payload: UserPasswordChange,
    db: DbSession,
    actor: CurrentUser,
) -> None:
    await UserService(db).change_password(user_id, payload, actor=actor)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.USER_DELETE)),
) -> None:
    await UserService(db).deactivate(user_id, actor=actor)