# app/modules/auth/enums.py
"""
Authentication enums.
"""

from enum import Enum
from app.shared.enums import BaseEnum

# ==================== AUTH ENUMS ====================

class TokenType(str, Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFICATION = "verification"
    API = "api"

class TokenStatus(str, Enum):
    """Token status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    USED = "used"

class AuthMethod(str, Enum):
    """Authentication methods"""
    PASSWORD = "password"
    OTP = "otp"
    TOTP = "totp"
    SOCIAL = "social"
    API_KEY = "api_key"
    BIOMETRIC = "biometric"
    MAGIC_LINK = "magic_link"
    
class AuthEventType(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_RESET = "password_reset"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"

class SessionStatus(str, Enum):
    """Session status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    TERMINATED = "terminated"

class LoginType(str, Enum):
    """Login types"""
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    ADMIN = "admin"
    STAFF = "staff"

class UserStatus(str, Enum):
    """User status"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DELETED = "deleted"

class VerificationType(str, Enum):
    """Verification types"""
    EMAIL = "email"
    PHONE = "phone"
    TWO_FACTOR = "two_factor"
    RESET_PASSWORD = "reset_password"
    SOCIAL_LINK = "social_link"

class TwoFactorType(str, Enum):
    """2FA types"""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODE = "backup_code"
    AUTHENTICATOR = "authenticator"

# ==================== PERMISSION ENUMS ====================

class PermissionCategory(str, Enum):
    """Permission categories"""
    USER = "user"
    AUTH = "auth"
    ORDER = "order"
    INVENTORY = "inventory"
    CUSTOMER = "customer"
    REPORT = "report"
    SETTINGS = "settings"
    SYSTEM = "system"
    WORKSHOP = "workshop"
    FINANCE = "finance"

class PermissionAction(str, Enum):
    """Permission actions"""
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"

# ==================== ROLE ENUMS ====================

class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    MECHANIC = "mechanic"
    CUSTOMER = "customer"
    GUEST = "guest"

class RoleType(str, Enum):
    """Role types"""
    SYSTEM = "system"      # System-defined roles
    CUSTOM = "custom"      # Custom-defined roles
    DEFAULT = "default"    # Default roles

# ==================== EXPORTS ====================

__all__ = [
    'TokenType',
    'TokenStatus',
    'AuthMethod',
    'SessionStatus',
    'LoginType',
    'UserStatus',
    'VerificationType',
    'TwoFactorType',
    'PermissionCategory',
    'PermissionAction',
    'UserRole',
    'RoleType',
]