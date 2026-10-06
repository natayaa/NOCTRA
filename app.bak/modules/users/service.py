from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import AuditAction
from core.exceptions import ConflictError, NotFoundError, ValidationError
from modules.audit.service import AuditService
from modules.auth.models import User
from modules.auth.passwords import hash_password, verify_password
from modules.rbac.repository import RoleRepository
from modules.users.repository import UserRepository
from modules.users.schemas import (
    UserCreate,
    UserPasswordChange,
    UserUpdate,
)


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    async def create(self, payload: UserCreate, *, actor: User) -> User:
        if await self.users.by_username(payload.username):
            raise ConflictError("Username already exists")
        if await self.users.by_email(payload.email):
            raise ConflictError("Email already exists")

        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            is_active=payload.is_active,
            is_superuser=payload.is_superuser,
        )
        user.roles = await self.roles.by_names(payload.role_names)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            new_data={"username": user.username, "email": user.email},
        )
        return user

    async def update(self, uid: UUID, payload: UserUpdate, *, actor: User) -> User:
        user = await self._get_or_404(uid)
        before = {"email": user.email, "full_name": user.full_name, "is_active": user.is_active}

        if payload.email and payload.email != user.email:
            if await self.users.by_email(payload.email):
                raise ConflictError("Email already exists")
            user.email = payload.email
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.role_names is not None:
            user.roles = await self.roles.by_names(payload.role_names)

        await self.db.flush()
        await self.db.refresh(user)

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            old_data=before,
            new_data={"email": user.email, "full_name": user.full_name, "is_active": user.is_active},
        )
        return user

    async def change_password(
        self, uid: UUID, payload: UserPasswordChange, *, actor: User
    ) -> None:
        user = await self._get_or_404(uid)
        if not verify_password(payload.old_password, user.hashed_password):
            raise ValidationError("Old password is incorrect")
        user.hashed_password = hash_password(payload.new_password)
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            new_data={"password_changed": True},
        )

    async def deactivate(self, uid: UUID, *, actor: User) -> None:
        user = await self._get_or_404(uid)
        user.is_active = False
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
        )

    async def _get_or_404(self, uid: UUID) -> User:
        user = await self.users.get(uid)
        if not user:
            raise NotFoundError("User not found")
        return user