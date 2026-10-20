"""User management business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction, RoleName
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.core.security import hash_password, verify_password
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.rbac.repository import RoleRepository
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    AdminPasswordReset,
    SelfPasswordChange,
    UserCreate,
    UserUpdate,
)


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    # ── Create ────────────────────────────────────────

    async def create(self, payload: UserCreate, *, actor: User) -> User:
        # Guard 1: privilege escalation — only superusers can create superusers.
        if payload.is_superuser and not actor.is_superuser:
            raise ForbiddenError(
                "Only a superuser can create another superuser"
            )

        # Guard 2: uniqueness
        if await self.users.by_username(payload.username):
            raise ConflictError("Username already exists")
        if await self.users.by_email(payload.email):
            raise ConflictError("Email already exists")

        # Guard 3: validate every requested role actually exists.
        roles = await self.roles.by_names(payload.role_names)
        found = {r.name for r in roles}
        missing = [n for n in payload.role_names if n not in found]
        if missing:
            raise ValidationError(
                f"Unknown role(s): {', '.join(missing)}",
                context={"roles_requested": payload.role_names, "missing": missing},
            )

        user = User(
            username=payload.username,
            email=str(payload.email),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            is_active=payload.is_active,
            is_superuser=payload.is_superuser,
            password_changed_at=datetime.now(UTC),
        )
        user.roles = roles
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            new_data={
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "roles": [r.name for r in roles],
            },
        )
        return user

    # ── Update ────────────────────────────────────────

    async def update(self, uid: UUID, payload: UserUpdate, *, actor: User) -> User:
        # Row lock prevents concurrent updates from racing.
        user = await self._get_or_404_for_update(uid)
        before = {
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "roles": sorted(r.name for r in user.roles),
        }

        # Guard: cannot deactivate yourself via update.
        if (
            "is_active" in payload.model_fields_set
            and payload.is_active is False
            and uid == actor.id
        ):
            raise ConflictError("Cannot deactivate your own account")

        # Guard: last superuser cannot be demoted via role removal.
        if "role_names" in payload.model_fields_set and payload.role_names is not None:
            roles = await self.roles.by_names(payload.role_names)
            found = {r.name for r in roles}
            missing = [n for n in payload.role_names if n not in found]
            if missing:
                raise ValidationError(
                    f"Unknown role(s): {', '.join(missing)}",
                    context={"roles_requested": payload.role_names, "missing": missing},
                )

            # Is this user currently the only active superuser?
            currently_super = user.is_superuser or any(
                r.name == RoleName.SUPERUSER.value for r in user.roles
            )
            will_still_be_super = user.is_superuser or any(
                r.name == RoleName.SUPERUSER.value for r in roles
            )
            if currently_super and not will_still_be_super:
                if await self.users.count_active_superusers() <= 1:
                    raise ConflictError(
                        "Cannot remove superuser privileges from the last "
                        "active superuser"
                    )

            user.roles = roles

        if "email" in payload.model_fields_set and payload.email is not None:
            new_email = str(payload.email)
            if new_email != user.email:
                if await self.users.by_email(new_email):
                    raise ConflictError("Email already exists")
                user.email = new_email

        if "full_name" in payload.model_fields_set:
            user.full_name = payload.full_name  # schema rejects None

        if "is_active" in payload.model_fields_set:
            # Guard: last superuser cannot be deactivated.
            if payload.is_active is False and self._is_superuser(user):
                if await self.users.count_active_superusers() <= 1:
                    raise ConflictError(
                        "Cannot deactivate the last active superuser"
                    )
            user.is_active = payload.is_active

        await self.db.flush()
        await self.db.refresh(user)

        after = {
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "roles": sorted(r.name for r in user.roles),
        }
        if before != after:
            await self.audit.log(
                action=AuditAction.UPDATE,
                table_name="users",
                record_id=user.id,
                user_id=actor.id,
                old_data=before,
                new_data=after,
            )
        return user

    # ── Self-service password ─────────────────────────

    async def change_own_password(
        self, uid: UUID, payload: SelfPasswordChange, *, actor: User
    ) -> None:
        # Guard: self-service only — actor.id MUST equal target.
        if uid != actor.id:
            raise ForbiddenError(
                "Use /users/{id}/reset-password with USER_UPDATE permission "
                "to change another user's password"
            )

        user = await self._get_or_404_for_update(uid)

        if not verify_password(payload.old_password, user.hashed_password):
            raise ValidationError("Old password is incorrect")

        user.hashed_password = hash_password(payload.new_password)
        user.password_changed_at = datetime.now(UTC)
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            new_data={"password_changed": True},
        )

    # ── Admin password reset ──────────────────────────

    async def reset_password(
        self, uid: UUID, payload: AdminPasswordReset, *, actor: User
    ) -> None:
        """
        Admin-driven reset. No old_password required — the endpoint's
        USER_UPDATE permission is the authorization. Cannot reset a
        superuser's password unless the actor is also a superuser.
        """
        user = await self._get_or_404_for_update(uid)

        if user.is_superuser and not actor.is_superuser:
            raise ForbiddenError(
                "Only a superuser can reset another superuser's password"
            )

        user.hashed_password = hash_password(payload.new_password)
        user.password_changed_at = datetime.now(UTC)
        # Reset lockout so the user can actually log in with the new password.
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            new_data={"password_reset_by_admin": True},
        )

    # ── Deactivate / Reactivate ───────────────────────

    async def deactivate(self, uid: UUID, *, actor: User) -> None:
        if uid == actor.id:
            raise ConflictError("Cannot deactivate your own account")

        user = await self._get_or_404_for_update(uid)

        if not user.is_active:
            return  # idempotent

        if self._is_superuser(user):
            if await self.users.count_active_superusers() <= 1:
                raise ConflictError(
                    "Cannot deactivate the last active superuser"
                )

        user.is_active = False
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            old_data={"is_active": True},
            new_data={"is_active": False},
        )

    async def reactivate(self, uid: UUID, *, actor: User) -> User:
        user = await self._get_or_404_for_update(uid)
        if user.is_active:
            return user  # idempotent

        user.is_active = True
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="users",
            record_id=user.id,
            user_id=actor.id,
            old_data={"is_active": False},
            new_data={"is_active": True},
        )
        return user

    # ── Helpers ───────────────────────────────────────

    @staticmethod
    def _is_superuser(user: User) -> bool:
        """True if the user has the superuser flag OR the superuser role."""
        return user.is_superuser or any(
            r.name == RoleName.SUPERUSER.value for r in user.roles
        )

    async def _get_or_404(self, uid: UUID) -> User:
        user = await self.users.get(uid)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def _get_or_404_for_update(self, uid: UUID) -> User:
        user = await self.users.get_for_update(uid)
        if not user:
            raise NotFoundError("User not found")
        return user