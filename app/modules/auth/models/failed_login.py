# app/modules/auth/models/failed_login.py
"""
Failed Login model for tracking failed login attempts.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, DateTime, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel
from app.modules.auth.enums import LoginType


class FailedLogin(BaseModel):
    """
    Failed Login model.
    
    Tracks failed login attempts for security monitoring and rate limiting.
    """
    
    __tablename__ = "tb_user_failed_logins"
    
    # ==================== FIELDS ====================
    
    identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Identifier (email, phone, username, or IP)"
    )
    identifier_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="email",
        doc="Type of identifier (email, phone, username, ip)"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        index=True,
        doc="IP address of the failed attempt"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="User agent string"
    )
    login_type: Mapped[LoginType] = mapped_column(
        String(20),
        nullable=False,
        default=LoginType.WEB,
        index=True,
        doc="Login type (web, mobile, api, etc)"
    )
    attempt_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="Time of the failed attempt"
    )
    reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Reason for failure"
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Error code"
    )
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional metadata (JSON object)"
    )
    
    # ==================== INDEXES ====================
    
    __table_args__ = (
        Index("idx_failed_logins_identifier_time", "identifier", "attempt_time"),
        Index("idx_failed_logins_ip_time", "ip_address", "attempt_time"),
    )
    
    # ==================== METHODS ====================
    
    @classmethod
    def create_from_request(
        cls,
        request,
        identifier: str,
        identifier_type: str = "email",
        reason: Optional[str] = None,
        error_code: Optional[str] = None,
        **kwargs
    ) -> "FailedLogin":
        """
        Create a failed login entry from a FastAPI request.
        
        Args:
            request: FastAPI Request object
            identifier: Identifier (email, phone, etc)
            identifier_type: Type of identifier
            reason: Reason for failure
            error_code: Error code
            **kwargs: Additional fields
        """
        return cls(
            identifier=identifier,
            identifier_type=identifier_type,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            reason=reason,
            error_code=error_code,
            **kwargs
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "identifier_type": self.identifier_type,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "login_type": self.login_type.value if self.login_type else None,
            "attempt_time": self.attempt_time.isoformat(),
            "reason": self.reason,
            "error_code": self.error_code,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


__all__ = ['FailedLogin']