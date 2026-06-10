from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    Standard API response.
    """
    success: bool = True
    message: str = "Success"
    data: T | None = None


class ErrorResponse(BaseModel):
    """
    Standard error response.
    """
    success: bool = False
    message: str
    errors: dict[str, Any] | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated API response.
    """
    success: bool = True
    message: str = "Success"

    total: int = 0
    page: int = 1
    page_size: int = 10

    data: list[T] = Field(default_factory=list)


class ListResponse(BaseModel, Generic[T]):
    """
    Non-paginated list response.
    """
    success: bool = True
    message: str = "Success"

    count: int = 0

    data: list[T] = Field(default_factory=list)


class BulkRequest(BaseModel, Generic[T]):
    """
    Generic bulk request payload.
    """
    results: list[T] = Field(
        default_factory=list,
        min_length=1,
    )