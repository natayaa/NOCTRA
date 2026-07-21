# modules/auth/__init__.py
"""
Authentication & Authorization Module

Module untuk mengelola:
- User management (CRUD)
- Authentication (Login, Register, Logout)
- Authorization (Role-based access control)
- Token management (JWT, Refresh Token)
- Password management (Hash, Reset, Change)
"""

from .models import User, Role, Permission, UserRole, RefreshToken
from .schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    UserRegister,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    UserRoleCreate,
    UserRoleUpdate,
    UserRoleResponse,
)
from .repository import UserRepository, RoleRepository, PermissionRepository, RefreshTokenRepository
from .services import AuthService, PasswordService, TokenService
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_permission,
    get_current_user_optional,
)
from .router import auth_router

__all__ = [
    # Models
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RefreshToken",
    # Schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "UserRegister",
    "TokenResponse",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "ResetPasswordRequest",
    "ForgotPasswordRequest",
    "UserRoleCreate",
    "UserRoleUpdate",
    "UserRoleResponse",
    # Repositories
    "UserRepository",
    "RoleRepository",
    "PermissionRepository",
    "RefreshTokenRepository",
    # Services
    "AuthService",
    "PasswordService",
    "TokenService",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_permission",
    "get_current_user_optional",
    # Router
    "auth_router",
]
