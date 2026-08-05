# app/shared/base_service.py
from typing import Optional, List, Dict, Any, TypeVar, Generic, Type, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.sql import Select
from uuid import UUID

from core.database import Base
from core.logging import get_logger, log_performance
from core.exceptions import NotFoundError, DuplicateError, ValidationError
from shared.base_model import BaseModel
from shared.pagination import PaginationParams, PaginatedResponse
from shared.filters import FilterParams, FilterCondition, FilterOperator

logger = get_logger(__name__)

# ==================== TYPE VARIABLES ====================

ModelType = TypeVar('ModelType', bound=BaseModel)
CreateSchemaType = TypeVar('CreateSchemaType')
UpdateSchemaType = TypeVar('UpdateSchemaType')

# ==================== BASE SERVICE ====================

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base service with CRUD operations.
    
    Usage:
        class UserService(BaseService[User, UserCreate, UserUpdate]):
            pass
    """
    
    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession
    ):
        self.model = model
        self.db = db
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== CRUD OPERATIONS ====================
    
    @log_performance(threshold_ms=500)
    async def create(
        self,
        data: CreateSchemaType,
        created_by: Optional[UUID] = None,
        **kwargs
    ) -> ModelType:
        """
        Create a new record.
        
        Args:
            data: Data for creating the record
            created_by: User ID who created the record
            **kwargs: Additional fields
        
        Returns:
            Created model instance
        """
        # Convert data to dict if it's a Pydantic model
        if hasattr(data, 'dict'):
            create_data = data.dict(exclude_unset=True)
        elif hasattr(data, 'model_dump'):
            create_data = data.model_dump(exclude_unset=True)
        else:
            create_data = dict(data) if data else {}
        
        # Add created_by if provided
        if created_by:
            create_data['created_by'] = created_by
        
        # Add any additional kwargs
        create_data.update(kwargs)
        
        # Create instance
        instance = self.model(**create_data)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        
        self.logger.info(f"Created {self.model.__name__}: {instance.id}")
        return instance
    
    @log_performance(threshold_ms=500)
    async def get(
        self,
        id: UUID,
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
        
        Returns:
            Model instance or None
        """
        query = select(self.model).where(self.model.id == id)
        
        if not include_deleted:
            query = query.where(self.model.is_active == True)
        
        result = await self.db.execute(query)
        instance = result.scalar_one_or_none()
        
        if not instance:
            self.logger.warning(f"{self.model.__name__} not found: {id}")
        
        return instance
    
    @log_performance(threshold_ms=500)
    async def get_or_raise(
        self,
        id: UUID,
        include_deleted: bool = False
    ) -> ModelType:
        """
        Get a record by ID or raise NotFoundError.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
        
        Returns:
            Model instance
        
        Raises:
            NotFoundError: If record not found
        """
        instance = await self.get(id, include_deleted)
        if not instance:
            raise NotFoundError(
                f"{self.model.__name__} with id {id} not found"
            )
        return instance
    
    @log_performance(threshold_ms=500)
    async def update(
        self,
        id: UUID,
        data: UpdateSchemaType,
        updated_by: Optional[UUID] = None,
        **kwargs
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            id: Record ID
            data: Data for updating the record
            updated_by: User ID who updated the record
            **kwargs: Additional fields
        
        Returns:
            Updated model instance
        
        Raises:
            NotFoundError: If record not found
        """
        # Get instance
        instance = await self.get_or_raise(id)
        
        # Convert data to dict if it's a Pydantic model
        if hasattr(data, 'dict'):
            update_data = data.dict(exclude_unset=True)
        elif hasattr(data, 'model_dump'):
            update_data = data.model_dump(exclude_unset=True)
        else:
            update_data = dict(data) if data else {}
        
        # Add updated_by if provided
        if updated_by:
            update_data['updated_by'] = updated_by
        
        # Add any additional kwargs
        update_data.update(kwargs)
        
        # Update instance
        for key, value in update_data.items():
            setattr(instance, key, value)
        
        await self.db.commit()
        await self.db.refresh(instance)
        
        self.logger.info(f"Updated {self.model.__name__}: {id}")
        return instance
    
    @log_performance(threshold_ms=500)
    async def delete(
        self,
        id: UUID,
        hard_delete: bool = False,
        deleted_by: Optional[UUID] = None
    ) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            hard_delete: If True, permanently delete from database
            deleted_by: User ID who deleted the record
        
        Returns:
            True if deleted successfully
        
        Raises:
            NotFoundError: If record not found
        """
        instance = await self.get_or_raise(id)
        
        if hard_delete:
            await self.db.delete(instance)
        else:
            # Soft delete
            instance.is_active = False
            if deleted_by:
                instance.updated_by = deleted_by
        
        await self.db.commit()
        
        self.logger.info(f"Deleted {self.model.__name__}: {id}")
        return True
    
    @log_performance(threshold_ms=500)
    async def restore(
        self,
        id: UUID,
        restored_by: Optional[UUID] = None
    ) -> ModelType:
        """
        Restore a soft-deleted record.
        
        Args:
            id: Record ID
            restored_by: User ID who restored the record
        
        Returns:
            Restored model instance
        
        Raises:
            NotFoundError: If record not found
        """
        instance = await self.get(id, include_deleted=True)
        if not instance:
            raise NotFoundError(
                f"{self.model.__name__} with id {id} not found"
            )
        
        instance.is_active = True
        if restored_by:
            instance.updated_by = restored_by
        
        await self.db.commit()
        await self.db.refresh(instance)
        
        self.logger.info(f"Restored {self.model.__name__}: {id}")
        return instance
    
    # ==================== LIST OPERATIONS ====================
    
    @log_performance(threshold_ms=500)
    async def list(
        self,
        pagination: Optional[PaginationParams] = None,
        filters: Optional[FilterParams] = None,
        **kwargs
    ) -> PaginatedResponse[ModelType]:
        """
        List records with pagination and filtering.
        
        Args:
            pagination: Pagination parameters
            filters: Filter parameters
            **kwargs: Additional filter conditions
        
        Returns:
            Paginated response with records
        """
        pagination = pagination or PaginationParams()
        filters = filters or FilterParams()
        
        # Build query
        query = self._build_list_query(filters, **kwargs)
        
        # Apply soft delete filter
        if not pagination.include_deleted:
            query = query.where(self.model.is_active == True)
        
        # Apply sorting
        query = self._apply_sorting(query, pagination)
        
        # Get total count
        count_query = self._build_count_query(filters, **kwargs)
        if not pagination.include_deleted:
            count_query = count_query.where(self.model.is_active == True)
        
        total = await self._get_count(count_query)
        
        # Apply pagination
        query = query.offset(pagination.skip).limit(pagination.limit)
        
        # Execute query
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
        )
    
    @log_performance(threshold_ms=500)
    async def list_all(
        self,
        filters: Optional[FilterParams] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[ModelType]:
        """
        List all records without pagination.
        
        Args:
            filters: Filter parameters
            limit: Maximum number of records to return
            **kwargs: Additional filter conditions
        
        Returns:
            List of records
        """
        filters = filters or FilterParams()
        
        # Build query
        query = self._build_list_query(filters, **kwargs)
        query = query.where(self.model.is_active == True)
        query = self._apply_sorting(query, PaginationParams(sort_by='created_at', sort_order='desc'))
        
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ==================== QUERY BUILDERS ====================
    
    def _build_list_query(
        self,
        filters: FilterParams,
        **kwargs
    ) -> Select:
        """Build list query with filters"""
        query = select(self.model)
        conditions = []
        
        # Add basic filters from kwargs
        for key, value in kwargs.items():
            if hasattr(self.model, key) and value is not None:
                conditions.append(getattr(self.model, key) == value)
        
        # Add filter params
        if filters.status:
            if hasattr(self.model, 'status'):
                if isinstance(filters.status, list):
                    conditions.append(self.model.status.in_(filters.status))
                else:
                    conditions.append(self.model.status == filters.status)
        
        if filters.is_active is not None and hasattr(self.model, 'is_active'):
            conditions.append(self.model.is_active == filters.is_active)
        
        # Add date filters
        if hasattr(self.model, 'created_at'):
            if filters.date_from:
                conditions.append(self.model.created_at >= filters.date_from)
            if filters.date_to:
                conditions.append(self.model.created_at <= filters.date_to)
        
        # Add custom filters
        for filter_cond in filters.custom_filters:
            condition = self._build_filter_condition(filter_cond)
            if condition is not None:
                conditions.append(condition)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def _build_count_query(
        self,
        filters: FilterParams,
        **kwargs
    ) -> Select:
        """Build count query with filters"""
        query = select(func.count()).select_from(self.model)
        conditions = []
        
        # Add basic filters from kwargs
        for key, value in kwargs.items():
            if hasattr(self.model, key) and value is not None:
                conditions.append(getattr(self.model, key) == value)
        
        # Add filter params
        if filters.status:
            if hasattr(self.model, 'status'):
                if isinstance(filters.status, list):
                    conditions.append(self.model.status.in_(filters.status))
                else:
                    conditions.append(self.model.status == filters.status)
        
        if filters.is_active is not None and hasattr(self.model, 'is_active'):
            conditions.append(self.model.is_active == filters.is_active)
        
        if filters.date_from and hasattr(self.model, 'created_at'):
            conditions.append(self.model.created_at >= filters.date_from)
        if filters.date_to and hasattr(self.model, 'created_at'):
            conditions.append(self.model.created_at <= filters.date_to)
        
        for filter_cond in filters.custom_filters:
            condition = self._build_filter_condition(filter_cond)
            if condition is not None:
                conditions.append(condition)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def _build_filter_condition(self, filter_cond: FilterCondition):
        """Build SQLAlchemy filter condition from FilterCondition"""
        if not hasattr(self.model, filter_cond.field):
            return None
        
        column = getattr(self.model, filter_cond.field)
        operator = filter_cond.operator
        value = filter_cond.value
        
        if operator == FilterOperator.EQUALS:
            return column == value
        elif operator == FilterOperator.NOT_EQUALS:
            return column != value
        elif operator == FilterOperator.CONTAINS:
            return column.ilike(f'%{value}%')
        elif operator == FilterOperator.STARTS_WITH:
            return column.ilike(f'{value}%')
        elif operator == FilterOperator.ENDS_WITH:
            return column.ilike(f'%{value}')
        elif operator == FilterOperator.GREATER_THAN:
            return column > value
        elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return column >= value
        elif operator == FilterOperator.LESS_THAN:
            return column < value
        elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return column <= value
        elif operator == FilterOperator.IN:
            return column.in_(value)
        elif operator == FilterOperator.NOT_IN:
            return column.not_in(value)
        elif operator == FilterOperator.BETWEEN:
            return column.between(value[0], value[1])
        elif operator == FilterOperator.IS_NULL:
            return column.is_(None)
        elif operator == FilterOperator.IS_NOT_NULL:
            return column.is_not(None)
        
        return None
    
    def _apply_sorting(self, query: Select, pagination: PaginationParams) -> Select:
        """Apply sorting to query"""
        if pagination.sort_by and hasattr(self.model, pagination.sort_by):
            column = getattr(self.model, pagination.sort_by)
            if pagination.sort_order == 'desc':
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            # Default sort by created_at desc
            if hasattr(self.model, 'created_at'):
                query = query.order_by(self.model.created_at.desc())
        
        return query
    
    async def _get_count(self, query: Select) -> int:
        """Get total count from query"""
        result = await self.db.execute(query)
        return result.scalar_one() or 0
    
    # ==================== BULK OPERATIONS ====================
    
    @log_performance(threshold_ms=1000)
    async def bulk_create(
        self,
        items: List[CreateSchemaType],
        created_by: Optional[UUID] = None
    ) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            items: List of data for creating records
            created_by: User ID who created the records
        
        Returns:
            List of created model instances
        """
        instances = []
        for data in items:
            if hasattr(data, 'dict'):
                create_data = data.dict(exclude_unset=True)
            elif hasattr(data, 'model_dump'):
                create_data = data.model_dump(exclude_unset=True)
            else:
                create_data = dict(data) if data else {}
            
            if created_by:
                create_data['created_by'] = created_by
            
            instance = self.model(**create_data)
            self.db.add(instance)
            instances.append(instance)
        
        await self.db.commit()
        
        # Refresh instances
        for instance in instances:
            await self.db.refresh(instance)
        
        self.logger.info(f"Bulk created {len(instances)} {self.model.__name__}")
        return instances
    
    @log_performance(threshold_ms=1000)
    async def bulk_delete(
        self,
        ids: List[UUID],
        hard_delete: bool = False
    ) -> int:
        """
        Delete multiple records in bulk.
        
        Args:
            ids: List of record IDs
            hard_delete: If True, permanently delete from database
        
        Returns:
            Number of records deleted
        """
        count = 0
        for id in ids:
            try:
                await self.delete(id, hard_delete)
                count += 1
            except NotFoundError:
                self.logger.warning(f"Record not found for deletion: {id}")
        
        self.logger.info(f"Bulk deleted {count} {self.model.__name__}")
        return count
    
    # ==================== VALIDATION ====================
    
    async def check_exists(
        self,
        field: str,
        value: Any,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if record exists with given field value"""
        if not hasattr(self.model, field):
            return False
        
        query = select(self.model).where(
            getattr(self.model, field) == value
        ).where(self.model.is_active == True)
        
        if exclude_id:
            query = query.where(self.model.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def validate_unique(
        self,
        field: str,
        value: Any,
        exclude_id: Optional[UUID] = None
    ) -> None:
        """Validate uniqueness of field value"""
        if await self.check_exists(field, value, exclude_id):
            raise DuplicateError(
                f"{self.model.__name__} with {field}={value} already exists"
            )

# ==================== EXPORTS ====================

__all__ = [
    'BaseService',
]