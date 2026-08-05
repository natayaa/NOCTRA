# app/core/__init__.py
"""
NOKTRA Autoworks Dashboard - Core Package
=========================================

Core modules for the NOKTRA Autoworks Dashboard Management System.

Modules:
    - config: Application configuration
    - database: Database connection and session management
    - security: Authentication, authorization, and security utilities
    - cache: Redis caching implementation
    - logging: Structured logging system
    - exceptions: Custom exceptions and error handlers
    - middleware: FastAPI middleware components
    - dependencies: Common FastAPI dependencies
    - constants: Core constants and enums
"""

from app.core.config import Settings, settings, get_settings, Environment
from app.core.database import DatabaseManager, Base, db_manager, get_db_session, get_raw_db_session
from app.core.security import (
    PasswordHandler,
    JWTManager,
    APIKeyManager,
    security_scheme,
    get_current_user,
    get_current_active_user,
    get_token_from_header,
    generate_random_token,
    generate_verification_code,
    generate_salt,
)
from app.core.cache import CacheManager, cache_manager, cached, invalidate_cache, CacheTTL
from app.core.logging import (
    get_logger,
    logger,
    setup_logging,
    LogContext,
    with_log_context,
    log_performance,
    request_id_var,
    user_id_var,
    correlation_id_var,
)
from app.core.exceptions import (
    CoreException,
    NotFoundError,
    DuplicateError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    ServiceError,
    RateLimitError,
    ErrorResponseFormatter,
    setup_exception_handlers,
)
from app.core.middleware import setup_middleware
from app.core.constants import (
    HTTPStatus,
    APIConstants,
    RegexPatterns,
    DateTimeConstants,
    FileConstants,
    Messages,
    CacheKeys,
    SortOrder,
    FilterOperators,
    LogLevel,
    CORSConstants,
    ResponseFields,
)
from app.core.dependencies import (
    PaginationParams,
    DateRangeParams,
    FilterParams,
    get_db,
    get_transaction_db,
    get_cache,
    get_request_logger,
    get_request_id,
    get_client_ip,
    get_user_agent,
    get_token_from_header as dep_get_token_from_header,
    validate_token,
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
    validate_uuid,
    validate_phone,
    validate_email,
    validate_plate_number,
    validate_nik,
    get_uuid_path,
    get_optional_uuid_path,
)

__version__ = "1.0.0"
__author__ = "NOKTRA Autoworks"

# Package exports
__all__ = [
    # Config
    "Settings",
    "settings",
    "get_settings",
    "Environment",
    
    # Database
    "DatabaseManager",
    "Base",
    "db_manager",
    "get_db_session",
    "get_raw_db_session",
    
    # Security
    "PasswordHandler",
    "JWTManager",
    "APIKeyManager",
    "security_scheme",
    "get_current_user",
    "get_current_active_user",
    "get_token_from_header",
    "generate_random_token",
    "generate_verification_code",
    "generate_salt",
    
    # Cache
    "CacheManager",
    "cache_manager",
    "cached",
    "invalidate_cache",
    "CacheTTL",
    
    # Logging
    "get_logger",
    "logger",
    "setup_logging",
    "LogContext",
    "with_log_context",
    "log_performance",
    "request_id_var",
    "user_id_var",
    "correlation_id_var",
    
    # Exceptions
    "CoreException",
    "NotFoundError",
    "DuplicateError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "DatabaseError",
    "ServiceError",
    "RateLimitError",
    "ErrorResponseFormatter",
    "setup_exception_handlers",
    
    # Middleware
    "setup_middleware",
    
    # Constants
    "HTTPStatus",
    "APIConstants",
    "RegexPatterns",
    "DateTimeConstants",
    "FileConstants",
    "Messages",
    "CacheKeys",
    "SortOrder",
    "FilterOperators",
    "LogLevel",
    "CORSConstants",
    "ResponseFields",
    
    # Dependencies
    "PaginationParams",
    "DateRangeParams",
    "FilterParams",
    "get_db",
    "get_transaction_db",
    "get_cache",
    "get_request_logger",
    "get_request_id",
    "get_client_ip",
    "get_user_agent",
    "validate_token",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "validate_uuid",
    "validate_phone",
    "validate_email",
    "validate_plate_number",
    "validate_nik",
    "get_uuid_path",
    "get_optional_uuid_path",
]

# Version info
__version_info__ = tuple(map(int, __version__.split('.')))