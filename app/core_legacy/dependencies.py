# core/dependencies.py
from typing import Optional, Type, TypeVar, List
from fastapi import Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.base import BaseResponse, PaginatedResponse, ErrorResponse


# =============================================================================
# Database Session - GUNAKAN get_db() LANGSUNG
# =============================================================================

async def get_session() -> AsyncSession:
    """
    Get database session.
    ⚠️ Menggunakan get_db() yang sudah proper.
    """
    async for session in get_db():
        return session


# =============================================================================
# Service Factory
# =============================================================================

T = TypeVar('T')


def get_service(service_class: Type[T]) -> Type[T]:
    """
    Factory untuk mendapatkan service dengan dependency injection.

    Usage:
        @router.get("/")
        async def list_items(
            service: InquiryService = Depends(get_service(InquiryService))
        ):
            ...
    """
    async def _get_service(
        db: AsyncSession = Depends(get_db)  # ✅ Langsung pakai get_db
    ) -> T:
        return service_class(db)
    return _get_service


# =============================================================================
# Pagination
# =============================================================================

class PaginationParams:
    """Common pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.limit = limit
        self.offset = (page - 1) * limit


# =============================================================================
# Query Parameters
# =============================================================================

class InquiryQueryParams:
    """Query parameters for inquiry endpoints."""

    def __init__(
        self,
        status: Optional[str] = Query(None, description="Filter by status"),
        search: Optional[str] = Query(
            None, description="Search by name, phone, vehicle"),
        brand: Optional[str] = Query(
            None, description="Filter by vehicle brand"),
        pagination: PaginationParams = Depends(),
    ):
        self.status = status
        self.search = search
        self.brand = brand
        self.page = pagination.page
        self.limit = pagination.limit
        self.offset = pagination.offset


class ProjectQueryParams:
    """Query parameters for project endpoints."""

    def __init__(
        self,
        status: Optional[str] = Query(None, description="Filter by status"),
        priority: Optional[str] = Query(
            None, description="Filter by priority"),
        search: Optional[str] = Query(
            None, description="Search by name, customer, vehicle"),
        brand: Optional[str] = Query(
            None, description="Filter by vehicle brand"),
        is_archived: bool = Query(False, description="Show archived projects"),
        stage_id: Optional[str] = Query(
            None, description="Filter by stage ID"),
        pagination: PaginationParams = Depends(),
    ):
        self.status = status
        self.priority = priority
        self.search = search
        self.brand = brand
        self.is_archived = is_archived
        self.stage_id = stage_id
        self.page = pagination.page
        self.limit = pagination.limit
        self.offset = pagination.offset


class InventoryQueryParams:
    """Query parameters for inventory endpoints."""

    def __init__(
        self,
        category: Optional[str] = Query(
            None, description="Filter by category"),
        status: Optional[str] = Query(None, description="Filter by status"),
        search: Optional[str] = Query(
            None, description="Search by name or SKU"),
        low_stock_only: bool = Query(
            False, description="Show only low stock items"),
        pagination: PaginationParams = Depends(),
    ):
        self.category = category
        self.status = status
        self.search = search
        self.low_stock_only = low_stock_only
        self.page = pagination.page
        self.limit = pagination.limit
        self.offset = pagination.offset


class PaymentQueryParams:
    """Query parameters for payment endpoints."""

    def __init__(
        self,
        payment_type: Optional[str] = Query(
            None, description="Filter by payment type"),
        status: Optional[str] = Query(None, description="Filter by status"),
        inquiry_id: Optional[str] = Query(
            None, description="Filter by inquiry ID"),
        pagination: PaginationParams = Depends(),
    ):
        self.payment_type = payment_type
        self.status = status
        self.inquiry_id = inquiry_id
        self.page = pagination.page
        self.limit = pagination.limit
        self.offset = pagination.offset


class PriceListQueryParams:
    """Query parameters for price list endpoints."""

    def __init__(
        self,
        category: Optional[str] = Query(
            None, description="Filter by category"),
        search: Optional[str] = Query(
            None, description="Search by name or description"),
        active_only: bool = Query(
            True, description="Only include active items"),
        vehicle_brand: Optional[str] = Query(
            None, description="Filter by vehicle brand"),
        vehicle_model: Optional[str] = Query(
            None, description="Filter by vehicle model"),
        pagination: PaginationParams = Depends(),
    ):
        self.category = category
        self.search = search
        self.active_only = active_only
        self.vehicle_brand = vehicle_brand
        self.vehicle_model = vehicle_model
        self.page = pagination.page
        self.limit = pagination.limit
        self.offset = pagination.offset


# =============================================================================
# Response Helpers
# =============================================================================

def success_response(data, message: str = "Success"):
    """Helper untuk success response."""
    return BaseResponse(success=True, message=message, data=data)


def error_response(message: str = "Error", errors: Optional[dict] = None, code: Optional[str] = None):
    """Helper untuk error response."""
    return ErrorResponse(success=False, message=message, errors=errors, code=code)


def paginated_response(
    items,
    total: int,
    page: int,
    page_size: int,
    message: str = "Success"
):
    """Helper untuk paginated response."""
    return PaginatedResponse.from_paginated(items, total, page, page_size, message)
