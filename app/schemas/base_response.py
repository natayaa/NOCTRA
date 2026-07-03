# schemas/base_response.py
from typing import Any, Generic, TypeVar, Optional, List

from pydantic import BaseModel, Field


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    Standard API response.
    """
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """
    Standard error response.
    """
    success: bool = False
    message: str
    errors: Optional[dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated API response.
    """
    success: bool = True
    message: str = "Success"

    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0

    data: List[T] = Field(default_factory=list)


class ListResponse(BaseModel, Generic[T]):
    """
    Non-paginated list response.
    """
    success: bool = True
    message: str = "Success"

    count: int = 0

    data: List[T] = Field(default_factory=list)


class BulkRequest(BaseModel, Generic[T]):
    """
    Generic bulk request payload.
    """
    results: List[T] = Field(
        default_factory=list,
        min_length=1,
    )