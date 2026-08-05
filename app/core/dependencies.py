# app/core/dependencies.py
from typing import Optional, List, Dict, Any, Union
from fastapi import Depends, Request, Query, Path, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timedelta

from .config import settings
from .database import get_db_session, db_manager
from .security import (
    get_current_user,
    get_current_active_user,
    JWTManager,
    security_scheme
)
from .cache import cache_manager
from .logging import get_logger, request_id_var
from .exceptions import AuthenticationError, ValidationError

# ==================== PAGINATION ====================

class PaginationParams:
    """
    Standard pagination parameters for API requests.
    
    Usage:
        @app.get("/items")
        async def get_items(pagination: PaginationParams = Depends()):
            skip = pagination.skip
            limit = pagination.limit
            ...
    """
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        sort_by: Optional[str] = Query(None, description="Sort by field"),
        sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
        search: Optional[str] = Query(None, description="Search query")
    ):
        self.page = page
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.search = search
        self.skip = (page - 1) * limit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "page": self.page,
            "limit": self.limit,
            "skip": self.skip,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "search": self.search
        }
    
    def get_skip(self) -> int:
        """Get skip value for database queries"""
        return self.skip
    
    def get_limit(self) -> int:
        """Get limit value for database queries"""
        return self.limit
    
    def get_sort_clause(self, model: Any) -> Optional[Any]:
        """
        Get sort clause for SQLAlchemy queries.
        
        Usage:
            query = query.order_by(pagination.get_sort_clause(MyModel))
        """
        if not self.sort_by or not hasattr(model, self.sort_by):
            return None
        
        column = getattr(model, self.sort_by)
        if self.sort_order == "desc":
            return column.desc()
        return column.asc()

# ==================== DATE RANGE ====================

class DateRangeParams:
    """
    Date range parameters for API requests.
    
    Usage:
        @app.get("/reports")
        async def get_reports(dates: DateRangeParams = Depends()):
            start = dates.start_date
            end = dates.end_date
            ...
    """
    
    def __init__(
        self,
        start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
        end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
        period: Optional[str] = Query(
            None,
            regex="^(today|yesterday|week|month|quarter|year)$",
            description="Predefined period"
        )
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.period = period
        
        # Set default to last 30 days if not provided
        if not start_date and not end_date and not period:
            self.end_date = datetime.utcnow()
            self.start_date = self.end_date - timedelta(days=30)
        
        # Handle predefined periods
        if period:
            now = datetime.utcnow()
            if period == "today":
                self.start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                self.end_date = now
            elif period == "yesterday":
                yesterday = now - timedelta(days=1)
                self.start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                self.end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            elif period == "week":
                self.start_date = now - timedelta(days=7)
                self.end_date = now
            elif period == "month":
                self.start_date = now - timedelta(days=30)
                self.end_date = now
            elif period == "quarter":
                self.start_date = now - timedelta(days=90)
                self.end_date = now
            elif period == "year":
                self.start_date = now - timedelta(days=365)
                self.end_date = now
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "period": self.period
        }

# ==================== FILTER PARAMS ====================

class FilterParams:
    """
    Generic filter parameters for API requests.
    
    Usage:
        @app.get("/items")
        async def get_items(filters: FilterParams = Depends()):
            status = filters.status
            ...
    """
    
    def __init__(
        self,
        status: Optional[Union[str, List[str]]] = Query(None, description="Filter by status"),
        category: Optional[Union[str, List[str]]] = Query(None, description="Filter by category"),
        tags: Optional[List[str]] = Query(None, description="Filter by tags"),
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        created_by: Optional[str] = Query(None, description="Filter by creator")
    ):
        self.status = status
        self.category = category
        self.tags = tags
        self.is_active = is_active
        self.created_by = created_by
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status,
            "category": self.category,
            "tags": self.tags,
            "is_active": self.is_active,
            "created_by": self.created_by
        }
    
    def get_status_list(self) -> List[str]:
        """Get status as list"""
        if isinstance(self.status, str):
            return [self.status]
        return self.status or []
    
    def get_category_list(self) -> List[str]:
        """Get category as list"""
        if isinstance(self.category, str):
            return [self.category]
        return self.category or []

# ==================== DATABASE DEPENDENCIES ====================

async def get_db() -> AsyncSession:
    """Dependency for database session"""
    async for session in get_db_session():
        yield session

async def get_transaction_db() -> AsyncSession:
    """
    Dependency for database session with explicit transaction control.
    Caller must handle commit/rollback.
    """
    if not db_manager.is_initialized:
        await db_manager.initialize()
    return await db_manager.get_raw_session()

# ==================== CACHE DEPENDENCY ====================

async def get_cache():
    """Dependency for cache manager"""
    return cache_manager

# ==================== LOGGING DEPENDENCY ====================

async def get_request_logger(request: Request):
    """Get logger with request context"""
    return get_logger("api")

# ==================== REQUEST INFO DEPENDENCIES ====================

async def get_request_id(request: Request) -> str:
    """Get request ID from request state"""
    return getattr(request.state, "request_id", "unknown")

async def get_client_ip(request: Request) -> str:
    """Get client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def get_user_agent(request: Request) -> str:
    """Get user agent from request"""
    return request.headers.get("user-agent", "unknown")

# ==================== AUTH DEPENDENCIES ====================

async def get_token_from_header(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Optional[str]:
    """Extract token from Authorization header"""
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]

async def validate_token(
    token: Optional[str] = Depends(get_token_from_header)
) -> Dict[str, Any]:
    """Validate JWT token and return payload"""
    if not token:
        raise AuthenticationError("Missing authentication token")
    
    return JWTManager.validate_token(token, token_type="access")

# ==================== RESPONSE MODELS ====================

class PaginatedResponse(BaseModel):
    """Standard paginated response model"""
    items: List[Any]
    total: int
    page: int
    limit: int
    pages: int
    
    @classmethod
    def from_paginator(cls, items: List[Any], total: int, page: int, limit: int):
        """Create from paginator results"""
        pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )

class SuccessResponse(BaseModel):
    """Standard success response model"""
    success: bool = True
    message: str
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    """Standard error response model"""
    success: bool = False
    error: Dict[str, Any]

# ==================== VALIDATOR DEPENDENCIES ====================

def validate_uuid(value: str) -> str:
    """Validate UUID format"""
    import re
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid UUID format",
            details={"field": "id", "value": value}
        )
    return value

def validate_phone(value: str) -> str:
    """Validate phone number format"""
    import re
    pattern = r'^\+?[0-9]{8,15}$'
    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid phone number",
            details={"field": "phone", "value": value}
        )
    return value

def validate_email(value: str) -> str:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid email format",
            details={"field": "email", "value": value}
        )
    return value

def validate_plate_number(value: str) -> str:
    """Validate Indonesian plate number"""
    import re
    pattern = r'^[A-Z]{1,2}\s?[0-9]{1,4}\s?[A-Z]{1,3}$'
    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid plate number",
            details={"field": "plate_number", "value": value}
        )
    return value

def validate_nik(value: str) -> str:
    """Validate Indonesian NIK (ID card number)"""
    import re
    pattern = r'^[0-9]{16}$'
    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid NIK format",
            details={"field": "nik", "value": value}
        )
    return value

# ==================== PATH PARAMETER DEPENDENCIES ====================

async def get_uuid_path(
    id: str = Path(..., description="UUID identifier")
) -> str:
    """Validate UUID path parameter"""
    return validate_uuid(id)

async def get_optional_uuid_path(
    id: Optional[str] = Path(None, description="UUID identifier")
) -> Optional[str]:
    """Validate optional UUID path parameter"""
    if id:
        return validate_uuid(id)
    return id

# ==================== EXPORTS ====================

__all__ = [
    # Pagination
    "PaginationParams",
    "DateRangeParams",
    "FilterParams",
    
    # Database
    "get_db",
    "get_transaction_db",
    
    # Cache
    "get_cache",
    
    # Logging
    "get_request_logger",
    
    # Request info
    "get_request_id",
    "get_client_ip",
    "get_user_agent",
    
    # Auth
    "get_token_from_header",
    "validate_token",
    
    # Response models
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    
    # Validators
    "validate_uuid",
    "validate_phone",
    "validate_email",
    "validate_plate_number",
    "validate_nik",
    
    # Path params
    "get_uuid_path",
    "get_optional_uuid_path",
]