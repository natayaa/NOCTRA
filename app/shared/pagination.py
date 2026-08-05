# app/shared/pagination.py
from typing import Optional, List, TypeVar, Generic, Any, Dict
from pydantic import BaseModel, Field
from math import ceil

from core.dependencies import PaginationParams as CorePaginationParams

# ==================== PAGINATION PARAMS ====================

class PaginationParams(CorePaginationParams):
    """
    Extended pagination parameters with additional features.
    """
    
    def __init__(
        self,
        page: int = 1,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        include_deleted: bool = False,
    ):
        super().__init__(page, limit, sort_by, sort_order, search)
        self.include_deleted = include_deleted
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()
        data['include_deleted'] = self.include_deleted
        return data

# ==================== PAGINATION RESPONSE ====================

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_previous: bool = Field(..., description="Has previous page")
    has_next: bool = Field(..., description="Has next page")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        limit: int
    ) -> "PaginatedResponse[T]":
        """Create paginated response from items and pagination params"""
        pages = ceil(total / limit) if limit > 0 else 0
        
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_previous=page > 1,
            has_next=page < pages,
        )
    
    @classmethod
    def from_paginator(
        cls,
        items: List[T],
        total: int,
        pagination: PaginationParams
    ) -> "PaginatedResponse[T]":
        """Create from paginator with pagination params"""
        return cls.create(
            items=items,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'items': self.items,
            'total': self.total,
            'page': self.page,
            'limit': self.limit,
            'pages': self.pages,
            'has_previous': self.has_previous,
            'has_next': self.has_next,
        }

# ==================== EXPORTS ====================

__all__ = [
    'PaginationParams',
    'PaginatedResponse',
]