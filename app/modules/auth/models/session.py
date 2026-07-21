# app/modules/auth/models/session.py
"""
Session model for user session management.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.modules.auth.enums import SessionStatus, LoginType

if TYPE_CHECKING:
    from app.modules.auth.models.user import User
    from app.modules.auth.models.access_token import AccessToken
    from app.modules.auth.models.refresh_token import RefreshToken
    from app.modules.auth.models.login_history import LoginHistory


class Session(BaseModel):
    """
    Session model.
    
    Manages user sessions across devices and platforms.
    """
    
    __tablename__ = "tb_user_sessions"
    
    # ==================== FIELDS ====================
    
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID this session belongs to"
    )
    session_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique session identifier"
    )
    login_type: Mapped[LoginType] = mapped_column(
        String(20),
        nullable=False,
        default=LoginType.WEB,
        index=True,
        doc="Login type (web, mobile, api, etc)"
    )
    status: Mapped[SessionStatus] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
        doc="Session status"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        doc="Session expiration timestamp"
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="Last activity timestamp"
    )
    terminated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp when session was terminated"
    )
    terminated_by: Mapped[Optional[UUID]] = mapped_column(
        nullable=True,
        doc="User ID who terminated this session"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        index=True,
        doc="IP address of the session"
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
        index=True,
        doc="Device type (mobile, desktop, tablet, etc)"
    )
    os_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Operating system name"
    )
    os_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Operating system version"
    )
    browser_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Browser name"
    )
    browser_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Browser version"
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
    is_2fa_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether 2FA was verified for this session"
    )
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional metadata (JSON object)"
    )
    
    # ==================== RELATIONSHIPS ====================
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
        lazy="selectin"
    )
    
    access_tokens: Mapped[List["AccessToken"]] = relationship(
        "AccessToken",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    login_histories: Mapped[List["LoginHistory"]] = relationship(
        "LoginHistory",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # ==================== INDEXES ====================
    
    __table_args__ = (
        Index("idx_sessions_user_status", "user_id", "status"),
        Index("idx_sessions_user_activity", "user_id", "last_activity"),
        Index("idx_sessions_device_user", "device_id", "user_id"),
        Index("idx_sessions_expires_status", "expires_at", "status"),
    )
    
    # ==================== PROPERTIES ====================
    
    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return (
            self.status == SessionStatus.ACTIVE
            and self.expires_at > datetime.utcnow()
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return self.expires_at <= datetime.utcnow()
    
    @property
    def is_terminated(self) -> bool:
        """Check if session is terminated."""
        return self.terminated_at is not None
    
    @property
    def time_remaining(self) -> Optional[int]:
        """Get seconds remaining until expiration."""
        if self.expires_at:
            remaining = (self.expires_at - datetime.utcnow()).total_seconds()
            return max(0, int(remaining))
        return None
    
    @property
    def idle_time(self) -> Optional[int]:
        """Get idle time in seconds."""
        if self.last_activity:
            idle = (datetime.utcnow() - self.last_activity).total_seconds()
            return int(idle)
        return None
    
    # ==================== METHODS ====================
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def expire(self) -> None:
        """Mark session as expired."""
        self.status = SessionStatus.EXPIRED
        self.expires_at = datetime.utcnow()
    
    def terminate(self, terminated_by: Optional[UUID] = None) -> None:
        """Terminate the session."""
        self.status = SessionStatus.TERMINATED
        self.terminated_at = datetime.utcnow()
        if terminated_by:
            self.terminated_by = terminated_by
    
    def verify_2fa(self) -> None:
        """Mark 2FA as verified."""
        self.is_2fa_verified = True
    
    def unverify_2fa(self) -> None:
        """Mark 2FA as unverified."""
        self.is_2fa_verified = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_token": self.session_token[:20] + "..." if self.session_token else None,
            "login_type": self.login_type.value if self.login_type else None,
            "status": self.status.value if self.status else None,
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "browser_name": self.browser_name,
            "browser_version": self.browser_version,
            "location": self.location,
            "country": self.country,
            "city": self.city,
            "is_2fa_verified": self.is_2fa_verified,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "is_terminated": self.is_terminated,
            "time_remaining": self.time_remaining,
            "idle_time": self.idle_time,
            "access_tokens_count": len(self.access_tokens) if self.access_tokens else 0,
            "refresh_tokens_count": len(self.refresh_tokens) if self.refresh_tokens else 0,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


__all__ = ['Session']