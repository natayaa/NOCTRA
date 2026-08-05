# app/modules/auth/models/login_history.py
"""
Login History model for tracking login events.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.modules.auth.enums import LoginType

if TYPE_CHECKING:
    from app.modules.auth.models.user import User
    from app.modules.auth.models.session import Session


class LoginHistory(BaseModel):
    """
    Login History model.
    
    Tracks all login attempts and sessions for audit purposes.
    """
    
    __tablename__ = "tb_login_histories"
    
    # ==================== FIELDS ====================
    
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID who attempted login"
    )
    session_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tb_user_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated session ID if successful"
    )
    login_type: Mapped[LoginType] = mapped_column(
        String(20),
        nullable=False,
        default=LoginType.WEB,
        index=True,
        doc="Login type (web, mobile, api, etc)"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        index=True,
        doc="IP address of the login attempt"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="User agent string"
    )
    device_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Device identifier"
    )
    device_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Device name"
    )
    device_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Device type (mobile, desktop, tablet, etc)"
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Geographic location"
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Country code"
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="City name"
    )
    login_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Login method (password, otp, social, etc)"
    )
    is_successful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Whether login was successful"
    )
    is_2fa_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether 2FA was required"
    )
    is_2fa_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether 2FA was verified"
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Reason for login failure"
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Error code if login failed"
    )
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional metadata (JSON object)"
    )
    
    # ==================== RELATIONSHIPS ====================
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="login_histories",
        lazy="selectin"
    )
    
    session: Mapped[Optional["Session"]] = relationship(
        "Session",
        back_populates="login_histories",
        lazy="selectin"
    )
    
    # ==================== INDEXES ====================
    
    __table_args__ = (
        Index("idx_login_histories_user_date", "user_id", "created_at"),
        Index("idx_login_histories_user_success", "user_id", "is_successful"),
        Index("idx_login_histories_ip", "ip_address"),
        Index("idx_login_histories_device", "device_id"),
    )
    
    # ==================== PROPERTIES ====================
    
    @property
    def is_suspicious(self) -> bool:
        """
        Check if login appears suspicious.
        This is a simple implementation - can be enhanced.
        """
        return not self.is_successful
    
    # ==================== METHODS ====================
    
    @classmethod
    def create_from_request(
        cls,
        request,
        user_id: UUID,
        login_type: LoginType,
        is_successful: bool = False,
        **kwargs
    ) -> "LoginHistory":
        """
        Create a login history entry from a FastAPI request.
        
        Args:
            request: FastAPI Request object
            user_id: User ID
            login_type: Type of login
            is_successful: Whether login was successful
            **kwargs: Additional fields
        """
        return cls(
            user_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            login_type=login_type,
            is_successful=is_successful,
            **kwargs
        )
    
    def mark_successful(self, session_id: UUID) -> None:
        """Mark login as successful with session ID."""
        self.is_successful = True
        self.session_id = session_id
    
    def mark_failed(self, reason: str, error_code: Optional[str] = None) -> None:
        """Mark login as failed with reason."""
        self.is_successful = False
        self.failure_reason = reason
        self.error_code = error_code
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": str(self.session_id) if self.session_id else None,
            "login_type": self.login_type.value if self.login_type else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "location": self.location,
            "country": self.country,
            "city": self.city,
            "login_method": self.login_method,
            "is_successful": self.is_successful,
            "is_2fa_required": self.is_2fa_required,
            "is_2fa_verified": self.is_2fa_verified,
            "failure_reason": self.failure_reason,
            "error_code": self.error_code,
            "is_suspicious": self.is_suspicious,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


__all__ = ['LoginHistory']