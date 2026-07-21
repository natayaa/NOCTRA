# app/core/exceptions.py
import logging
import traceback

from typing_extensions import Optional, Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from datetime import datetime

logger = logging.getLogger(__name__)

# ==================== BASE EXCEPTION ====================

class CoreException(Exception):
    """Base exception for core module"""
    
    def __init__(
        self,
        message: str,
        code: str = "CORE_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

# ==================== SPECIFIC EXCEPTIONS ====================

class NotFoundError(CoreException):
    """Resource not found exception"""
    
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

class DuplicateError(CoreException):
    """Duplicate entry exception"""
    
    def __init__(
        self,
        message: str = "Duplicate entry",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="DUPLICATE_ENTRY",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )

class ValidationError(CoreException):
    """Validation error exception"""
    
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class AuthenticationError(CoreException):
    """Authentication error exception"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class AuthorizationError(CoreException):
    """Authorization error exception"""
    
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class DatabaseError(CoreException):
    """Database error exception"""
    
    def __init__(
        self,
        message: str = "Database error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class ServiceError(CoreException):
    """External service error exception"""
    
    def __init__(
        self,
        message: str = "Service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )

class RateLimitError(CoreException):
    """Rate limit exceeded exception"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )

# ==================== ERROR RESPONSE FORMATTER ====================

class ErrorResponseFormatter:
    """Format error responses consistently"""
    
    @staticmethod
    def format(
        message: str,
        code: str = "ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format error response"""
        response = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        if details:
            response["error"]["details"] = details
        
        if request_id:
            response["error"]["request_id"] = request_id
        
        if path:
            response["error"]["path"] = path
        
        if method:
            response["error"]["method"] = method
        
        return response
    
    @staticmethod
    def to_json_response(
        message: str,
        code: str = "ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> JSONResponse:
        """Create JSON error response"""
        content = ErrorResponseFormatter.format(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            request_id=request_id,
            path=path,
            method=method
        )
        return JSONResponse(
            status_code=status_code,
            content=content
        )

# ==================== EXCEPTION HANDLERS ====================

def setup_exception_handlers(app: FastAPI) -> None:
    """Setup all exception handlers for FastAPI application"""
    
    @app.exception_handler(CoreException)
    async def core_exception_handler(request: Request, exc: CoreException):
        """Handle custom core exceptions"""
        logger.warning(
            f"Core exception: {exc.code} - {exc.message}",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "details": exc.details
            }
        )
        
        return ErrorResponseFormatter.to_json_response(
            message=exc.message,
            code=exc.code,
            status_code=exc.status_code,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
            path=str(request.url.path),
            method=request.method
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={
                "path": str(request.url.path),
                "method": request.method
            }
        )
        
        return ErrorResponseFormatter.to_json_response(
            message=str(exc.detail),
            code=f"HTTP_{exc.status_code}",
            status_code=exc.status_code,
            request_id=request.headers.get("X-Request-ID"),
            path=str(request.url.path),
            method=request.method
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", "")
            })
        
        logger.warning(
            f"Validation error: {errors}",
            extra={
                "path": str(request.url.path),
                "method": request.method
            }
        )
        
        return ErrorResponseFormatter.to_json_response(
            message="Request validation failed",
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": errors},
            request_id=request.headers.get("X-Request-ID"),
            path=str(request.url.path),
            method=request.method
        )
    
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """Handle database integrity errors"""
        logger.error(
            f"Integrity error: {str(exc)}",
            extra={
                "path": str(request.url.path),
                "method": request.method
            }
        )
        
        # Check for duplicate key violations
        if "duplicate key" in str(exc).lower():
            code = "DUPLICATE_ENTRY"
            status_code = status.HTTP_409_CONFLICT
            message = "Duplicate entry"
        else:
            code = "DATABASE_INTEGRITY_ERROR"
            status_code = status.HTTP_400_BAD_REQUEST
            message = "Database integrity error"
        
        return ErrorResponseFormatter.to_json_response(
            message=message,
            code=code,
            status_code=status_code,
            details={"error": str(exc)} if app.debug else None,
            request_id=request.headers.get("X-Request-ID"),
            path=str(request.url.path),
            method=request.method
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle SQLAlchemy errors"""
        logger.error(
            f"Database error: {str(exc)}\n{traceback.format_exc()}",
            extra={
                "path": str(request.url.path),
                "method": request.method
            }
        )
        
        return ErrorResponseFormatter.to_json_response(
            message="Database error occurred",
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error": str(exc)} if app.debug else None,
            request_id=request.headers.get("X-Request-ID"),
            path=str(request.url.path),
            method=request.method
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(
            f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}",
            extra={
                "path": str(request.url.path),
                "method": request.method
            }
        )
        
        return ErrorResponseFormatter.to_json_response(
            message="Internal server error",
            code="INTERNAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "error": str(exc),
                "traceback": traceback.format_exc().split("\n")
            } if app.debug else None,
            request_id=request.headers.get("X-Request-ID"),
            path=str(request.url.path),
            method=request.method
        )
    
    logger.info("Exception handlers configured")

# ==================== EXPORTS ====================

__all__ = [
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
    
    # Formatter
    "ErrorResponseFormatter",
    
    # Setup
    "setup_exception_handlers",
]