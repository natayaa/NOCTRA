from typing_extensions import Optional, Any, Dict, List, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')

# ==================== BASE RESPONSE ====================

class BaseResponse(BaseModel):
    """Base response model"""
    
    success: bool = Field(True, description="Success status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }

# ==================== SUCCESS RESPONSE ====================

class SuccessResponse(BaseResponse, Generic[T]):
    """Success response with data"""
    
    data: Optional[T] = Field(None, description="Response data")
    
    @classmethod
    def create(
        cls,
        message: str,
        data: Optional[T] = None
    ) -> "SuccessResponse[T]":
        """Create success response"""
        return cls(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.utcnow(),
        )

# ==================== LIST RESPONSE ====================

class ListResponse(BaseResponse):
    """List response with items"""
    
    items: List[Any] = Field(default_factory=list, description="List of items")
    count: int = Field(0, description="Number of items")
    
    @classmethod
    def create(
        cls,
        message: str,
        items: List[Any]
    ) -> "ListResponse":
        """Create list response"""
        return cls(
            success=True,
            message=message,
            items=items,
            count=len(items),
            timestamp=datetime.utcnow(),
        )

# ==================== ERROR RESPONSE ====================

class ErrorDetail(BaseModel):
    """Error detail model"""
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field name if validation error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class ErrorResponse(BaseModel):
    """Error response model"""
    
    success: bool = Field(False, description="Success status")
    error: ErrorDetail = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> "ErrorResponse":
        """Create error response"""
        return cls(
            success=False,
            error=ErrorDetail(
                code=code,
                message=message,
                field=field,
                details=details,
            ),
            timestamp=datetime.utcnow(),
        )

# ==================== RESPONSE UTILITIES ====================

class ResponseBuilder:
    """Builder for creating consistent responses"""
    
    @staticmethod
    def success(
        message: str,
        data: Optional[Any] = None
    ) -> SuccessResponse:
        """Create success response"""
        return SuccessResponse.create(message, data)
    
    @staticmethod
    def list(
        message: str,
        items: List[Any]
    ) -> ListResponse:
        """Create list response"""
        return ListResponse.create(message, items)
    
    @staticmethod
    def error(
        code: str,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse:
        """Create error response"""
        return ErrorResponse.create(code, message, field, details)

# ==================== EXPORTS ====================

__all__ = [
    'BaseResponse',
    'SuccessResponse',
    'ListResponse',
    'ErrorResponse',
    'ErrorDetail',
    'ResponseBuilder',
]