# core/base.py
from datetime import datetime
from typing import Optional, Any, Generic, TypeVar, List, Dict, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from sqlalchemy import DateTime, func, select, delete, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# SQLAlchemy Base Models
# =============================================================================

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class UUIDMixin:
    """Mixin for UUID primary key."""
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        index=True
    )


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )


class SoftDeleteMixin:
    """Mixin for soft delete."""
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True
    )


# =============================================================================
# Base Repository
# =============================================================================

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base Repository dengan operasi CRUD dasar.
    ⚠️ TIDAK ADA flush(), refresh(), atau commit() di sini!
    Semua transaction dikelola oleh Service.
    """

    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model

    # ==================== CREATE ====================

    async def create(self, data: Union[ModelType, Dict[str, Any]]) -> ModelType:
        """
        Create a single instance - TANPA flush.

        Args:
            data: Either a model instance or dictionary of attributes

        Returns:
            The created model instance (same object, not refreshed)
        """
        if isinstance(data, dict):
            instance = self.model(**data)
        else:
            instance = data

        self.db.add(instance)
        return instance

    async def create_from_dict(self, data: Dict[str, Any]) -> ModelType:
        """Create instance from dictionary - TANPA flush."""
        instance = self.model(**data)
        self.db.add(instance)
        return instance

    async def bulk_create(self, instances: List[Union[ModelType, Dict[str, Any]]]) -> List[ModelType]:
        """
        Bulk create instances - TANPA flush.

        Args:
            instances: List of model instances or dictionaries

        Returns:
            List of created model instances
        """
        model_instances = []
        for item in instances:
            if isinstance(item, dict):
                instance = self.model(**item)
            else:
                instance = item
            model_instances.append(instance)

        self.db.add_all(model_instances)
        return model_instances

    # ==================== READ ====================

    async def get(self, pk: Any) -> Optional[ModelType]:
        """Get by primary key."""
        return await self.db.get(self.model, pk)

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = True,
        **filters
    ) -> List[ModelType]:
        """Get all with filters."""
        stmt = select(self.model)

        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)

        if order_by:
            column = getattr(self.model, order_by, None)
            if column:
                stmt = stmt.order_by(column.desc() if descending else column)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_one(self, **filters) -> Optional[ModelType]:
        """Get one by filters."""
        stmt = select(self.model)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self, **filters) -> int:
        """Count with filters."""
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def exists(self, **filters) -> bool:
        """Check if any exists with filters."""
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)

        result = await self.db.execute(stmt)
        return result.scalar_one() > 0

    # ==================== UPDATE ====================

    async def update(self, pk: Any, data: Union[Dict[str, Any], BaseModel]) -> Optional[ModelType]:
        """
        Update by primary key - TANPA flush/refresh.
        ⚠️ Hanya mengubah atribut, tidak menyimpan ke database!
        """
        obj = await self.get(pk)
        if not obj:
            return None

        if hasattr(data, "model_dump"):
            data = data.model_dump(exclude_unset=True)

        for key, value in data.items():
            if hasattr(obj, key) and value is not None:
                setattr(obj, key, value)

        return obj

    async def update_many(
        self,
        filters: Dict[str, Any],
        data: Dict[str, Any]
    ) -> int:
        """
        Update many with filters - TANPA flush.
        ⚠️ Eksekusi UPDATE langsung, tapi tidak flush!
        """
        stmt = update(self.model).where(
            *[getattr(self.model, k) == v for k, v in filters.items()]
        ).values(**data)

        result = await self.db.execute(stmt)
        return result.rowcount

    # ==================== DELETE ====================

    async def delete(self, pk: Any) -> bool:
        """
        Delete by primary key - TANPA flush.
        ⚠️ Hanya menandai untuk dihapus, tidak menyimpan ke database!
        """
        obj = await self.get(pk)
        if not obj:
            return False

        await self.db.delete(obj)
        return True

    async def delete_many(self, **filters) -> int:
        """
        Delete many with filters - TANPA flush.
        ⚠️ Eksekusi DELETE langsung, tapi tidak flush!
        """
        stmt = delete(self.model).where(
            *[getattr(self.model, k) == v for k, v in filters.items()]
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def soft_delete(self, pk: Any) -> bool:
        """
        Soft delete by primary key - TANPA flush.
        ⚠️ Hanya mengubah atribut, tidak menyimpan ke database!
        """
        obj = await self.get(pk)
        if not obj:
            return False

        if hasattr(obj, "is_deleted"):
            obj.is_deleted = True
            obj.deleted_at = datetime.now()
        elif hasattr(obj, "is_active"):
            obj.is_active = False
        else:
            return await self.delete(pk)

        return True


# =============================================================================
# Pydantic Response Schemas
# =============================================================================

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standard API response."""
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None

    @classmethod
    def success_response(cls, data: T, message: str = "Success") -> "BaseResponse[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_response(cls, message: str = "Error", data: Optional[T] = None) -> "BaseResponse[T]":
        return cls(success=False, message=message, data=data)


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    message: str
    errors: Optional[Dict[str, Any]] = None
    code: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response."""
    success: bool = True
    message: str = "Success"
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0
    data: List[T] = Field(default_factory=list)

    @classmethod
    def from_paginated(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
        message: str = "Success"
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            success=True,
            message=message,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=items
        )


class ListResponse(BaseModel, Generic[T]):
    """Non-paginated list response."""
    success: bool = True
    message: str = "Success"
    count: int = 0
    data: List[T] = Field(default_factory=list)


class BulkRequest(BaseModel, Generic[T]):
    """Generic bulk request payload."""
    items: List[T] = Field(
        default_factory=list,
        min_length=1,
        description="List of items to process"
    )
    action: Optional[str] = Field(
        None, description="Action to perform: create, update, delete"
    )


# =============================================================================
# Type Aliases
# =============================================================================

JSONDict = Dict[str, Any]
