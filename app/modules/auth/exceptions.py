# app/modules/auth/exceptions.py
"""
Authentication exceptions.
"""

from typing import Optional, Dict, Any
from app.core.exceptions import CoreException
from fastapi import status

# ==================== AUTH EXCEPTIONS ====================

class AuthException(CoreException):
    """Base authentication exception"""
    
    def __init__(
        self,
        message: str = "Authentication error",
        code: str = "AUTH_ERROR",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, code, status_code, details)

class InvalidCredentialsError(AuthException):
    """Invalid credentials error"""
    
    def __init__(
        self,
        message: str = "Invalid email or password",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="INVALID_CREDENTIALS",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class AccountLockedError(AuthException):
    """Account locked error"""
    
    def __init__(
        self,
        message: str = "Account has been locked",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="ACCOUNT_LOCKED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class AccountSuspendedError(AuthException):
    """Account suspended error"""
    
    def __init__(
        self,
        message: str = "Account has been suspended",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="ACCOUNT_SUSPENDED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class AccountBannedError(AuthException):
    """Account banned error"""
    
    def __init__(
        self,
        message: str = "Account has been banned",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="ACCOUNT_BANNED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class AccountNotVerifiedError(AuthException):
    """Account not verified error"""
    
    def __init__(
        self,
        message: str = "Account not verified",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="ACCOUNT_NOT_VERIFIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class TokenExpiredError(AuthException):
    """Token expired error"""
    
    def __init__(
        self,
        message: str = "Token has expired",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="TOKEN_EXPIRED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class TokenInvalidError(AuthException):
    """Token invalid error"""
    
    def __init__(
        self,
        message: str = "Invalid token",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="TOKEN_INVALID",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class TokenRevokedError(AuthException):
    """Token revoked error"""
    
    def __init__(
        self,
        message: str = "Token has been revoked",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="TOKEN_REVOKED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class TokenMissingError(AuthException):
    """Token missing error"""
    
    def __init__(
        self,
        message: str = "Authentication token required",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="TOKEN_MISSING",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class PermissionDeniedError(AuthException):
    """Permission denied error"""
    
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class TwoFactorRequiredError(AuthException):
    """Two-factor authentication required"""
    
    def __init__(
        self,
        message: str = "Two-factor authentication required",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="2FA_REQUIRED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class TwoFactorInvalidError(AuthException):
    """Invalid 2FA code"""
    
    def __init__(
        self,
        message: str = "Invalid 2FA code",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="2FA_INVALID",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class RateLimitExceededError(AuthException):
    """Rate limit exceeded"""
    
    def __init__(
        self,
        message: str = "Too many attempts. Please try again later.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )

class SocialAuthError(AuthException):
    """Social authentication error"""
    
    def __init__(
        self,
        message: str = "Social authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="SOCIAL_AUTH_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )

class UserExistsError(AuthException):
    """User already exists"""
    
    def __init__(
        self,
        message: str = "User already exists",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="USER_EXISTS",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )

class UserNotFoundError(AuthException):
    """User not found"""
    
    def __init__(
        self,
        message: str = "User not found",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="USER_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

# ==================== EXPORTS ====================

__all__ = [
    'AuthException',
    'InvalidCredentialsError',
    'AccountLockedError',
    'AccountSuspendedError',
    'AccountBannedError',
    'AccountNotVerifiedError',
    'TokenExpiredError',
    'TokenInvalidError',
    'TokenRevokedError',
    'TokenMissingError',
    'PermissionDeniedError',
    'TwoFactorRequiredError',
    'TwoFactorInvalidError',
    'RateLimitExceededError',
    'SocialAuthError',
    'UserExistsError',
    'UserNotFoundError',
]