# app/modules/auth/models/user.py
"""
User model for authentication and user management.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, DateTime, Boolean, Index, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.modules.auth.enums import UserStatus, UserRole, AuthMethod

if TYPE_CHECKING:
    from app.modules.auth.models.session import Session
    from app.modules.auth.models.login_history import LoginHistory


class User(BaseModel):
    """
    User model.
    
    Stores user account information and authentication data.
    """
    
    __tablename__ = "tb_users"
    
    # ==================== FIELDS ====================
    
    # Core fields
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="User email address"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
        index=True,
        doc="User phone number"
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        index=True,
        doc="Username"
    )
    
    # Authentication
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Hashed password"
    )
    auth_method: Mapped[AuthMethod] = mapped_column(
        String(20),
        nullable=False,
        default=AuthMethod.PASSWORD,
        index=True,
        doc="Authentication method"
    )
    
    # Status
    status: Mapped[UserStatus] = mapped_column(
        String(20),
        nullable=False,
        default=UserStatus.PENDING,
        index=True,
        doc="User account status"
    )
    role: Mapped[UserRole] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.CUSTOMER,
        index=True,
        doc="User role"
    )
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Full name"
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="First name"
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Last name"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Profile picture URL"
    )
    
    # Verification
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Email verification timestamp"
    )
    phone_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Phone verification timestamp"
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Whether email is verified"
    )
    is_phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Whether phone is verified"
    )
    
    # Security
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Last login timestamp"
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="Last login IP address"
    )
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Last password change timestamp"
    )
    password_reset_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether password reset is required"
    )
    
    # 2FA
    is_2fa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether 2FA is enabled"
    )
    totp_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="TOTP secret key"
    )
    backup_codes: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Backup codes for 2FA"
    )
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional metadata (JSON object)"
    )
    locale: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        default="en",
        doc="User locale preference"
    )
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="User timezone"
    )
    
    # ==================== RELATIONSHIPS ====================
    
    sessions: Mapped[List["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    login_histories: Mapped[List["LoginHistory"]] = relationship(
        "LoginHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # ==================== INDEXES ====================
    
    __table_args__ = (
        Index("idx_users_status_role", "status", "role"),
        Index("idx_users_email_status", "email", "status"),
        Index("idx_users_phone_status", "phone", "status"),
        Index("idx_users_last_login", "last_login_at"),
        Index("idx_users_email_verified", "is_email_verified"),
        Index("idx_users_phone_verified", "is_phone_verified"),
    )
    
    # ==================== PROPERTIES ====================
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_pending(self) -> bool:
        """Check if user account is pending verification."""
        return self.status == UserStatus.PENDING
    
    @property
    def is_suspended(self) -> bool:
        """Check if user account is suspended."""
        return self.status == UserStatus.SUSPENDED
    
    @property
    def is_banned(self) -> bool:
        """Check if user account is banned."""
        return self.status == UserStatus.BANNED
    
    @property
    def is_deleted(self) -> bool:
        """Check if user account is deleted."""
        return self.status == UserStatus.DELETED
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_manager(self) -> bool:
        """Check if user is manager."""
        return self.role == UserRole.MANAGER
    
    @property
    def is_staff(self) -> bool:
        """Check if user is staff-level."""
        return self.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF]
    
    @property
    def is_mechanic(self) -> bool:
        """Check if user is mechanic."""
        return self.role == UserRole.MECHANIC
    
    @property
    def is_customer(self) -> bool:
        """Check if user is customer."""
        return self.role == UserRole.CUSTOMER
    
    @property
    def full_name_or_email(self) -> str:
        """Get full name or email if name is not set."""
        return self.full_name or self.email
    
    @property
    def display_name(self) -> str:
        """Get display name (first_name + last_name or full_name or email)."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.full_name:
            return self.full_name
        return self.email
    
    # ==================== METHODS ====================
    
    def verify_email(self) -> None:
        """Mark email as verified."""
        self.is_email_verified = True
        self.email_verified_at = datetime.utcnow()
    
    def verify_phone(self) -> None:
        """Mark phone as verified."""
        self.is_phone_verified = True
        self.phone_verified_at = datetime.utcnow()
    
    def update_last_login(self, ip_address: Optional[str] = None) -> None:
        """Update last login information."""
        self.last_login_at = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address
    
    def change_password(self, new_password_hash: str) -> None:
        """Change user password."""
        self.password_hash = new_password_hash
        self.password_changed_at = datetime.utcnow()
        self.password_reset_required = False
    
    def require_password_reset(self) -> None:
        """Require password reset on next login."""
        self.password_reset_required = True
    
    def enable_2fa(self, totp_secret: str, backup_codes: List[str]) -> None:
        """Enable 2FA for user."""
        self.is_2fa_enabled = True
        self.totp_secret = totp_secret
        self.backup_codes = backup_codes
    
    def disable_2fa(self) -> None:
        """Disable 2FA for user."""
        self.is_2fa_enabled = False
        self.totp_secret = None
        self.backup_codes = None
    
    def activate(self) -> None:
        """Activate user account."""
        self.status = UserStatus.ACTIVE
    
    def suspend(self) -> None:
        """Suspend user account."""
        self.status = UserStatus.SUSPENDED
    
    def ban(self, reason: Optional[str] = None) -> None:
        """Ban user account."""
        self.status = UserStatus.BANNED
        if reason:
            self.metadata = {**(self.metadata or {}), "ban_reason": reason}
    
    def unban(self) -> None:
        """Unban user account."""
        self.status = UserStatus.ACTIVE
        if self.metadata:
            self.metadata.pop("ban_reason", None)
    
    def to_dict(self) -> dict:
        """Convert to dictionary (excluding sensitive data)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "phone": self.phone,
            "username": self.username,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "avatar_url": self.avatar_url,
            "status": self.status.value if self.status else None,
            "role": self.role.value if self.role else None,
            "auth_method": self.auth_method.value if self.auth_method else None,
            "is_email_verified": self.is_email_verified,
            "is_phone_verified": self.is_phone_verified,
            "is_2fa_enabled": self.is_2fa_enabled,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "locale": self.locale,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "is_pending": self.is_pending,
            "is_suspended": self.is_suspended,
            "is_banned": self.is_banned,
            "is_admin": self.is_admin,
            "is_manager": self.is_manager,
            "is_staff": self.is_staff,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def to_dict_full(self) -> dict:
        """Convert to dictionary with all fields (including sensitive)."""
        result = self.to_dict()
        result.update({
            "password_hash": self.password_hash,
            "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
            "phone_verified_at": self.phone_verified_at.isoformat() if self.phone_verified_at else None,
            "last_login_ip": self.last_login_ip,
            "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
            "password_reset_required": self.password_reset_required,
            "metadata": self.metadata,
        })
        return result


__all__ = ['User']