from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        # Covers: action=? ORDER BY created_at DESC
        Index("ix_audit_logs_action_created", "action", "created_at"),
        # Covers: table_name=? AND record_id=?  (record history lookups)
        Index("ix_audit_logs_table_record", "table_name", "record_id"),
        # Covers: ORDER BY created_at DESC  (default unfiltered listing)
        Index("ix_audit_logs_created_at", "created_at"),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # No standalone index — covered by ix_audit_logs_action_created prefix.
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    old_data: Mapped[dict | None] = mapped_column(JSONB)
    new_data: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.table_name}#{self.record_id}>"