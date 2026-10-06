from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base, TimestampMixin, UUIDMixin


class AppSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    is_secret: Mapped[bool] = mapped_column(default=False, nullable=False)