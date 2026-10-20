from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.rbac.models import Role, UserRole  # noqa: F401


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


    # Set whenever password changes (self or admin reset). Every access
    # token issued BEFORE this timestamp is rejected by `get_current_user`.
    # This is the only mechanism we have to force-logout a user, since we
    # use stateless JWTs (no session store).
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    
    roles: Mapped[list[Role]] = relationship(
        secondary=UserRole.__table__,
        back_populates="users",
        lazy="selectin",
    )