# core/filters.py
from typing import Optional, List, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime


class FilterParams(BaseModel):
    """Base filter parameters."""
    search: Optional[str] = Field(None, description="Search term")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    offset: int = Field(0, ge=0, description="Offset")
    sort_by: Optional[str] = Field(None, description="Sort by field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")

    def to_dict(self) -> dict:
        """Convert to dict for query."""
        return self.model_dump(exclude_unset=True)


class DateRangeFilter(BaseModel):
    """Date range filter."""
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")


class SearchFilter(BaseModel):
    """Search filter."""
    query: str = Field(..., min_length=1, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search")


class SortOption(BaseModel):
    """Sort option."""
    field: str = Field(..., description="Field to sort by")
    order: str = Field("asc", description="Sort order (asc/desc)")
