"""Email log — a record of every email the system has attempted to send."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.email.constants import EmailStatus


class EmailLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "email_logs"
    __table_args__ = (
        # Covers: status=? ORDER BY created_at DESC
        Index("ix_email_logs_status_created", "status", "created_at"),
        # Covers: template=? lookups
        Index("ix_email_logs_template", "template"),
        # Covers: (related_type, related_id) — entity history lookups
        Index("ix_email_logs_related", "related_type", "related_id"),
    )

    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    to_name: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    # No standalone index — covered by ix_email_logs_status_created prefix.
    status: Mapped[str] = mapped_column(
        String(16),
        default=EmailStatus.PENDING.value,
        server_default=EmailStatus.PENDING.value,
        nullable=False,
    )

    # Optional link to a domain object (e.g. INQUIRY + inquiry_id)
    related_type: Mapped[str | None] = mapped_column(String(32))
    related_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<EmailLog {self.template} → {self.to_email} [{self.status}]>"