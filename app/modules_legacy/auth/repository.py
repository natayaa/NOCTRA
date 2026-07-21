# modules/auth/repository.py
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, delete
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from core.constants import UserStatus
from .models import User, Role, Permission, UserRole, RolePermission, RefreshToken


class UserRepository(BaseRepository[User]):
    """Repository untuk User."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=User)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, username_or_email: str) -> Optional[User]:
        """Get user by username or email."""
        stmt = select(User).where(
            or_(
                User.username == username_or_email,
                User.email == username_or_email
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: UUID) -> Optional[User]:
        """Get user with roles and permissions."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.roles)
                .selectinload(UserRole.role)
                .selectinload(Role.permissions)
                .selectinload(RolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Get all active users."""
        stmt = (
            select(User)
            .where(User.status == UserStatus.ACTIVE)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_last_login(self, user_id: UUID, ip_address: Optional[str] = None) -> Optional[User]:
        """Update last login timestamp."""
        user = await self.get(user_id)
        if not user:
            return None

        user.last_login = datetime.now()
        if ip_address:
            user.last_ip = ip_address

        # Reset failed login attempts
        user.failed_login_attempts = 0

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def increment_failed_login(self, user_id: UUID) -> Optional[User]:
        """Increment failed login attempts."""
        user = await self.get(user_id)
        if not user:
            return None

        user.failed_login_attempts += 1

        # Lock user after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.status = UserStatus.LOCKED
            user.locked_until = datetime.now() + timedelta(minutes=30)

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def reset_failed_login(self, user_id: UUID) -> Optional[User]:
        """Reset failed login attempts."""
        user = await self.get(user_id)
        if not user:
            return None

        user.failed_login_attempts = 0
        if user.status == UserStatus.LOCKED:
            user.status = UserStatus.ACTIVE
            user.locked_until = None

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_user_permissions(self, user_id: UUID) -> List[str]:
        """Get all permissions for a user."""
        # Get user with roles and permissions
        user = await self.get_with_roles(user_id)
        if not user:
            return []

        permissions = set()

        # If superuser, return all permissions
        if user.is_superuser:
            stmt = select(Permission.name)
            result = await self.db.execute(stmt)
            return result.scalars().all()

        for user_role in user.roles:
            if user_role.role and user_role.role.is_active:
                for role_perm in user_role.role.permissions:
                    if role_perm.permission and role_perm.permission.is_active:
                        permissions.add(role_perm.permission.name)

        return list(permissions)

    async def get_user_roles(self, user_id: UUID) -> List[str]:
        """Get all role names for a user."""
        user = await self.get_with_roles(user_id)
        if not user:
            return []

        return [ur.role.name for ur in user.roles if ur.role and ur.role.is_active]

    async def assign_role(self, user_id: UUID, role_id: UUID, assigned_by: Optional[UUID] = None) -> Optional[UserRole]:
        """Assign role to user."""
        # Check if already assigned
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by
        )
        self.db.add(user_role)
        await self.db.flush()
        await self.db.refresh(user_role)
        return user_role

    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove role from user."""
        stmt = delete(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def get_online_users(self, minutes: int = 5) -> List[User]:
        """Get users online in last N minutes."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        stmt = (
            select(User)
            .where(
                User.last_login >= cutoff,
                User.status == UserStatus.ACTIVE
            )
            .order_by(User.last_login.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


class RoleRepository(BaseRepository[Role]):
    """Repository untuk Role."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=Role)

    async def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        stmt = select(Role).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_permissions(self, role_id: UUID) -> Optional[Role]:
        """Get role with permissions."""
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def assign_permission(self, role_id: UUID, permission_id: UUID) -> Optional[RolePermission]:
        """Assign permission to role."""
        stmt = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        role_perm = RolePermission(
            role_id=role_id,
            permission_id=permission_id
        )
        self.db.add(role_perm)
        await self.db.flush()
        await self.db.refresh(role_perm)
        return role_perm

    async def remove_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        """Remove permission from role."""
        stmt = delete(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0


class PermissionRepository(BaseRepository[Permission]):
    """Repository untuk Permission."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=Permission)

    async def get_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        stmt = select(Permission).where(Permission.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_module(self, module: str) -> List[Permission]:
        """Get permissions by module."""
        stmt = select(Permission).where(Permission.module == module)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_default_permissions(self) -> List[Permission]:
        """Get default permissions for new user."""
        # Return basic permissions
        stmt = select(Permission).where(
            Permission.module.in_(["profile", "dashboard"]),
            Permission.action.in_(["read", "update"])
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository untuk Refresh Token."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=RefreshToken)

    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string."""
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_token(
        self,
        user_id: UUID,
        token: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> RefreshToken:
        """Create new refresh token."""
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(refresh_token)
        await self.db.flush()
        await self.db.refresh(refresh_token)
        return refresh_token

    async def revoke_token(self, token: str, reason: Optional[str] = None) -> bool:
        """Revoke a refresh token."""
        refresh_token = await self.get_by_token(token)
        if not refresh_token:
            return False

        refresh_token.revoked_at = datetime.now()
        refresh_token.revoked_reason = reason
        await self.db.flush()
        return True

    async def revoke_all_user_tokens(self, user_id: UUID, reason: Optional[str] = None) -> int:
        """Revoke all refresh tokens for a user."""
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None)
        )
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        for token in tokens:
            token.revoked_at = datetime.now()
            token.revoked_reason = reason

        await self.db.flush()
        return len(tokens)

    async def cleanup_expired_tokens(self) -> int:
        """Delete expired refresh tokens."""
        stmt = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.now())
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
