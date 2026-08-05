# app/modules/auth/models/access_token.py
"""
Access Token model for JWT token management.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.modules.auth.enums import TokenStatus

if TYPE_CHECKING:
    from app.modules.auth.models.session import Session


class AccessToken(BaseModel):
    """
    Access Token model.
    
    Stores JWT access tokens for validation and revocation.
    """
    
    __tablename__ = "tb_user_access_tokens"
    
    # ==================== FIELDS ====================
    
    token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        doc="JWT token string"
    )
    jti: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        doc="JWT ID (unique identifier)"
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated session ID"
    )
    user_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
        doc="User ID this token belongs to"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        doc="Token expiration timestamp"
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp when token was revoked"
    )
    revoked_by: Mapped[Optional[UUID]] = mapped_column(
        nullable=True,
        doc="User ID who revoked this token"
    )
    status: Mapped[TokenStatus] = mapped_column(
        String(20),
        nullable=False,
        default=TokenStatus.ACTIVE,
        index=True,
        doc="Token status"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address when token was issued"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User agent when token was issued"
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Last time token was used"
    )
    metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Additional metadata (JSON string)"
    )
    
    # ==================== RELATIONSHIPS ====================
    
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="access_tokens",
        lazy="selectin"
    )
    
    # ==================== INDEXES ====================
    
    __table_args__ = (
        Index("idx_access_tokens_user_expires", "user_id", "expires_at"),
        Index("idx_access_tokens_session_status", "session_id", "status"),
    )
    
    # ==================== PROPERTIES ====================
    
    @property
    def is_active(self) -> bool:
        """Check if token is active and not expired."""
        return (
            self.status == TokenStatus.ACTIVE
            and self.expires_at > datetime.utcnow()
            and self.revoked_at is None
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return self.expires_at <= datetime.utcnow()
    
    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None
    
    # ==================== METHODS ====================
    
    def revoke(self, revoked_by: Optional[UUID] = None) -> None:
        """Revoke the token."""
        self.status = TokenStatus.REVOKED
        self.revoked_at = datetime.utcnow()
        if revoked_by:
            self.revoked_by = revoked_by
    
    def use(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "token": self.token[:20] + "..." if self.token else None,  # Truncate for security
            "jti": self.jti,
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "expires_at": self.expires_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "status": self.status.value if self.status else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "is_revoked": self.is_revoked,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


__all__ = ['AccessToken']