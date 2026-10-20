from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class AppSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
    )
    value: Mapped[str | None] = mapped_column(Text)
    # No standalone index — categories are few and small; the unique
    # key index plus a full scan of this tiny table is fast enough.
    category: Mapped[str] = mapped_column(
        String(50), default="general", server_default="general", nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(255))
    is_secret: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
    )

    def __repr__(self) -> str:
        masked = "***" if self.is_secret and self.value else self.value
        return f"<AppSetting {self.key}={masked!r}>"