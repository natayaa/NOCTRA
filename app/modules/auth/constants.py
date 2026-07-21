# app/modules/auth/constants.py
"""
Authentication constants.
"""

from typing import Dict, Any

# ==================== AUTH CONSTANTS ====================

class AuthConstants:
    """Authentication constants"""
    
    # Token types
    TOKEN_TYPE_ACCESS = "access"
    TOKEN_TYPE_REFRESH = "refresh"
    TOKEN_TYPE_RESET = "reset"
    TOKEN_TYPE_VERIFICATION = "verification"
    TOKEN_TYPE_API = "api"
    
    # Token expiry (seconds)
    TOKEN_EXPIRY = {
        TOKEN_TYPE_ACCESS: 3600,           # 1 hour
        TOKEN_TYPE_REFRESH: 604800,        # 7 days
        TOKEN_TYPE_RESET: 1800,            # 30 minutes
        TOKEN_TYPE_VERIFICATION: 86400,    # 24 hours
        TOKEN_TYPE_API: 31536000,          # 1 year
    }
    
    # Rate limits (requests per period)
    RATE_LIMIT_LOGIN = 10       # 10 attempts per 5 minutes
    RATE_LIMIT_REGISTER = 5     # 5 attempts per hour
    RATE_LIMIT_RESET = 3        # 3 attempts per hour
    RATE_LIMIT_VERIFY = 10      # 10 attempts per 5 minutes
    
    # Rate limit periods (seconds)
    RATE_LIMIT_PERIOD_LOGIN = 300      # 5 minutes
    RATE_LIMIT_PERIOD_REGISTER = 3600  # 1 hour
    RATE_LIMIT_PERIOD_RESET = 3600     # 1 hour
    RATE_LIMIT_PERIOD_VERIFY = 300     # 5 minutes
    
    # Session
    SESSION_MAX_AGE = 86400  # 24 hours
    SESSION_REFRESH_THRESHOLD = 3600  # 1 hour
    
    # Password
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 72
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Verification code
    VERIFICATION_CODE_LENGTH = 6
    VERIFICATION_CODE_EXPIRY = 300  # 5 minutes
    VERIFICATION_CODE_MAX_ATTEMPTS = 3
    
    # Cache keys
    CACHE_KEY_USER = "auth:user:{user_id}"
    CACHE_KEY_USER_PERMISSIONS = "auth:user:{user_id}:permissions"
    CACHE_KEY_USER_ROLES = "auth:user:{user_id}:roles"
    CACHE_KEY_TOKEN_BLACKLIST = "auth:token:blacklist:{token_id}"
    CACHE_KEY_LOGIN_ATTEMPTS = "auth:login:attempts:{identifier}"
    CACHE_KEY_RESET_TOKEN = "auth:reset:token:{token}"
    CACHE_KEY_VERIFICATION_CODE = "auth:verify:code:{identifier}"
    
    # Cache TTL (seconds)
    CACHE_TTL_USER = 3600           # 1 hour
    CACHE_TTL_PERMISSIONS = 3600    # 1 hour
    CACHE_TTL_ROLES = 3600          # 1 hour
    CACHE_TTL_TOKEN_BLACKLIST = 86400  # 24 hours
    CACHE_TTL_LOGIN_ATTEMPTS = 300  # 5 minutes
    CACHE_TTL_RESET_TOKEN = 1800    # 30 minutes
    CACHE_TTL_VERIFICATION = 300    # 5 minutes
    
    # Headers
    HEADER_AUTHORIZATION = "Authorization"
    HEADER_X_API_KEY = "X-API-Key"
    HEADER_X_USER_ID = "X-User-ID"
    HEADER_X_SESSION_ID = "X-Session-ID"
    
    # Cookie names
    COOKIE_ACCESS_TOKEN = "access_token"
    COOKIE_REFRESH_TOKEN = "refresh_token"
    COOKIE_SESSION = "session"
    
    # Default roles
    DEFAULT_ROLES = {
        "admin": "Administrator with full access",
        "manager": "Manager with elevated access",
        "staff": "Staff with limited access",
        "mechanic": "Mechanic with workshop access",
        "customer": "Customer with basic access",
    }
    
    # Default permissions
    DEFAULT_PERMISSIONS = {
        # User management
        "users:view": "View users",
        "users:create": "Create users",
        "users:update": "Update users",
        "users:delete": "Delete users",
        "users:roles": "Manage user roles",
        
        # Auth
        "auth:login": "Login to system",
        "auth:logout": "Logout from system",
        "auth:refresh": "Refresh token",
        "auth:reset": "Reset password",
        "auth:verify": "Verify account",
        
        # Orders
        "orders:view": "View orders",
        "orders:create": "Create orders",
        "orders:update": "Update orders",
        "orders:delete": "Delete orders",
        "orders:status": "Change order status",
        "orders:assign": "Assign orders",        # Tambahkan
        "orders:approve": "Approve orders",      # Tambahkan
        
        # Inventory
        "inventory:view": "View inventory",
        "inventory:create": "Create inventory",
        "inventory:update": "Update inventory",
        "inventory:delete": "Delete inventory",
        "inventory:stock": "Manage stock",
        
        # Customers
        "customers:view": "View customers",
        "customers:create": "Create customers",
        "customers:update": "Update customers",
        "customers:delete": "Delete customers",
        
        # Reports
        "reports:view": "View reports",
        "reports:generate": "Generate reports",
        "reports:export": "Export reports",
        
        # Settings
        "settings:view": "View settings",
        "settings:update": "Update settings",
    }

# ==================== OTP/TOTP CONSTANTS ====================

class OTPConstants:
    """OTP/TOTP constants"""
    
    # TOTP
    TOTP_ISSUER = "NOKTRA Autoworks"
    TOTP_DIGITS = 6
    TOTP_INTERVAL = 30  # seconds
    TOTP_ALGORITHM = "SHA1"
    
    # SMS OTP
    SMS_OTP_LENGTH = 6
    SMS_OTP_EXPIRY = 300  # 5 minutes
    SMS_OTP_MAX_ATTEMPTS = 3
    
    # Recovery codes
    RECOVERY_CODE_COUNT = 10
    RECOVERY_CODE_LENGTH = 16

# ==================== SOCIAL AUTH CONSTANTS ====================

class SocialAuthConstants:
    """Social authentication constants"""
    
    PROVIDERS = {
        "google": {
            "name": "Google",
            "icon": "google",
            "color": "#EA4335",
        },
        "facebook": {
            "name": "Facebook",
            "icon": "facebook",
            "color": "#1877F2",
        },
        "apple": {
            "name": "Apple",
            "icon": "apple",
            "color": "#000000",
        },
        "github": {
            "name": "GitHub",
            "icon": "github",
            "color": "#181717",
        },
        "microsoft": {
            "name": "Microsoft",
            "icon": "microsoft",
            "color": "#00A4EF",
        },
    }

# ==================== EXPORTS ====================

__all__ = [
    'AuthConstants',
    'OTPConstants',
    'SocialAuthConstants',
]