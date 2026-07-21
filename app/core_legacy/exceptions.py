# core/exceptions.py
from fastapi.responses import JSONResponse
from fastapi import Request
from typing import Optional, Dict, Any
from fastapi import status


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ConflictError(AppException):
    """Resource conflict error."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class UnauthorizedError(AppException):
    """Unauthorized access error."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    """Forbidden access error."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class BusinessError(AppException):
    """Business rule violation error."""

    def __init__(self, message: str = "Business rule violation"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class DatabaseError(AppException):
    """Database error."""

    def __init__(self, message: str = "Database error"):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceUnavailableError(AppException):
    """Service unavailable error."""

    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class RateLimitError(AppException):
    """Rate limit exceeded error."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


# =============================================================================
# Exception Handlers (untuk FastAPI)
# =============================================================================


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler untuk AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "code": exc.code,
            "details": exc.details
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler untuk exception umum."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "code": "INTERNAL_SERVER_ERROR"
        }
    )
