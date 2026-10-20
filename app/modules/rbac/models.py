from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = (
        # For filtering system vs custom roles in admin UI
        Index("ix_roles_is_system", "is_system"),
    )

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False,
    )

    # `lazy="selectin"` is safe here: permissions per role is small and
    # frequently accessed by permission checks in admin UI.
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )

    # `lazy="raise"` is CRITICAL for this relationship:
    # 1. Privacy — loading a Role must NOT silently expose all its users.
    # 2. Performance — `User.roles` (selectin) would otherwise cascade:
    #    load user → load roles → load all users with those roles → ...
    # Any code that genuinely needs `role.users` must explicitly
    # `selectinload(Role.users)` — an intentional speed bump.
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        secondary="user_roles",
        back_populates="roles",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        # Reverse lookup: "who has role X?" — composite PK (user_id, role_id)
        # already covers "user's roles", but not "role's users".
        Index("ix_user_roles_role", "role_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Permission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list[Role]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        # Reverse lookup: "which roles have permission X?"
        Index("ix_role_permissions_permission", "permission_id"),
    )

    role_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )