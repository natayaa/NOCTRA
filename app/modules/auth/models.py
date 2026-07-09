# modules/auth/models.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional

from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey,
    Integer, Index, CheckConstraint, func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin
from core.constants import UserStatus


class User(Base, UUIDMixin, TimestampMixin):
    """Model untuk user."""
    __tablename__ = "tb_users"

    # ============ Core Fields ============
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ============ Profile ============
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ============ Status & Metadata ============
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserStatus.ACTIVE, index=True
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ============ Relationships ============
    roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="[UserRole.user_id]",  # <-- Tambahkan ini
        primaryjoin="User.id == UserRole.user_id"  # <-- Tambahkan ini
    )

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="[RefreshToken.user_id]"  # <-- Tambahkan ini
    )

    # Tambahkan relationship untuk assigned_by
    assigned_roles = relationship(
        "UserRole",
        foreign_keys="[UserRole.assigned_by]",
        primaryjoin="User.id == UserRole.assigned_by",
        viewonly=True,
        lazy="selectin"
    )
    # ============ Constraints ============
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'locked')",
            name="ck_user_status"
        ),
        Index("idx_user_email_status", "email", "status"),
        Index("idx_user_username_status", "username", "status"),
    )

    def __repr__(self):
        return f"<User {self.id} - {self.username} - {self.email}>"

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @property
    def is_locked(self) -> bool:
        if not self.locked_until:
            return False
        return datetime.now() < self.locked_until

    @property
    def display_name(self) -> str:
        return self.full_name or self.username


class Role(Base, UUIDMixin, TimestampMixin):
    """Model untuk role."""
    __tablename__ = "tb_roles"

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)

    # ============ Relationships ============
    users = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        foreign_keys="[UserRole.role_id]",  # <-- Tambahkan ini
    )
    permissions = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="[RolePermission.role_id]",  # <-- Tambahkan ini
    )

    def __repr__(self):
        return f"<Role {self.id} - {self.name}>"


class Permission(Base, UUIDMixin, TimestampMixin):
    """Model untuk permission."""
    __tablename__ = "tb_permissions"

    # Format: module:action (e.g., project:create, payment:view)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # create, read, update, delete, manage
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    # ============ Relationships ============
    roles = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_permission_module_action", "module", "action"),
        UniqueConstraint("module", "action",
                         name="uq_permission_module_action"),
    )

    def __repr__(self):
        return f"<Permission {self.id} - {self.name}>"


class UserRole(Base, UUIDMixin, TimestampMixin):
    """Model untuk relasi User-Role."""
    __tablename__ = "tb_user_roles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_roles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    assigned_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ============ Relationships ============
    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="users", foreign_keys=[role_id])
    assigner = relationship("User", foreign_keys=[
                            assigned_by], back_populates="assigned_roles")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("idx_user_role_user", "user_id"),
        Index("idx_user_role_role", "role_id"),
    )

    def __repr__(self):
        return f"<UserRole {self.user_id} - {self.role_id}>"


class RolePermission(Base, UUIDMixin, TimestampMixin):
    """Model untuk relasi Role-Permission."""
    __tablename__ = "tb_role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_roles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_permissions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ============ Relationships ============
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id",
                         name="uq_role_permission"),
        Index("idx_role_permission_role", "role_id"),
        Index("idx_role_permission_permission", "permission_id"),
    )

    def __repr__(self):
        return f"<RolePermission {self.role_id} - {self.permission_id}>"


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    """Model untuk refresh token."""
    __tablename__ = "tb_refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ============ Relationships ============
    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_token_user", "user_id"),
        Index("idx_refresh_token_expires", "expires_at"),
        Index("idx_refresh_token_revoked", "revoked_at"),
    )

    def __repr__(self):
        return f"<RefreshToken {self.id} - {self.user_id}>"

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_revoked
