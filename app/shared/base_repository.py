# app/shared/base_repository.py
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, TypeVar, Generic, Type, Union, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete, update
from sqlalchemy.sql import Select
from sqlalchemy.orm import selectinload, joinedload
from uuid import UUID
from datetime import datetime

from core.database import Base
from core.logging import get_logger, log_performance
from core.exceptions import NotFoundError, DatabaseError
from shared.base_model import BaseModel
from shared.pagination import PaginationParams, PaginatedResponse
from shared.filters import FilterParams, FilterCondition, FilterOperator

logger = get_logger(__name__)

# ==================== TYPE VARIABLES ====================

ModelType = TypeVar('ModelType', bound=BaseModel)

# ==================== BASE REPOSITORY ====================

class BaseRepository(Generic[ModelType]):
    """
    Base repository with CRUD operations.
    
    Repository pattern separates database logic from business logic.
    
    Usage:
        class UserRepository(BaseRepository[User]):
            async def find_by_email(self, email: str) -> Optional[User]:
                return await self.get_by_field('email', email)
    """
    
    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession
    ):
        self.model = model
        self.db = db
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== CORE CRUD OPERATIONS ====================
    
    @log_performance(threshold_ms=500)
    async def create(
        self,
        data: Dict[str, Any],
        commit: bool = True
    ) -> ModelType:
        """
        Create a new record.
        
        Args:
            data: Dictionary of field values
            commit: Whether to commit immediately
        
        Returns:
            Created model instance
        """
        try:
            instance = self.model(**data)
            self.db.add(instance)
            
            if commit:
                await self.db.commit()
                await self.db.refresh(instance)
            else:
                await self.db.flush()
            
            self.logger.debug(f"Created {self.model.__name__}: {instance.id}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to create record: {str(e)}")
    
    @log_performance(threshold_ms=500)
    async def get(
        self,
        id: UUID,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
        
        Returns:
            Model instance or None
        """
        try:
            query = self._build_base_query(include_deleted)
            query = self._apply_relations(query, load_relations)
            query = query.where(self.model.id == id)
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Failed to get {self.model.__name__} by id {id}: {str(e)}")
            raise DatabaseError(f"Failed to fetch record: {str(e)}")
    
    @log_performance(threshold_ms=500)
    async def get_or_raise(
        self,
        id: UUID,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> ModelType:
        """
        Get a record by ID or raise NotFoundError.
        
        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
        
        Returns:
            Model instance
        
        Raises:
            NotFoundError: If record not found
        """
        instance = await self.get(id, include_deleted, load_relations)
        if not instance:
            raise NotFoundError(
                f"{self.model.__name__} with id {id} not found"
            )
        return instance
    
    @log_performance(threshold_ms=500)
    async def get_by_field(
        self,
        field: str,
        value: Any,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> Optional[ModelType]:
        """
        Get a record by field value.
        
        Args:
            field: Field name
            value: Field value
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
        
        Returns:
            Model instance or None
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field '{field}' does not exist on {self.model.__name__}")
        
        try:
            query = self._build_base_query(include_deleted)
            query = self._apply_relations(query, load_relations)
            query = query.where(getattr(self.model, field) == value)
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Failed to get {self.model.__name__} by {field}={value}: {str(e)}")
            raise DatabaseError(f"Failed to fetch record: {str(e)}")
    
    @log_performance(threshold_ms=500)
    async def update(
        self,
        id: UUID,
        data: Dict[str, Any],
        commit: bool = True
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            id: Record ID
            data: Dictionary of field values to update
            commit: Whether to commit immediately
        
        Returns:
            Updated model instance
        
        Raises:
            NotFoundError: If record not found
        """
        try:
            instance = await self.get_or_raise(id)
            
            # Update fields
            for key, value in data.items():
                if hasattr(instance, key) and key not in ['id', 'created_at', 'created_by']:
                    setattr(instance, key, value)
            
            # Update timestamp
            if hasattr(instance, 'updated_at'):
                instance.updated_at = datetime.utcnow()
            
            if commit:
                await self.db.commit()
                await self.db.refresh(instance)
            else:
                await self.db.flush()
            
            self.logger.debug(f"Updated {self.model.__name__}: {id}")
            return instance
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to update {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to update record: {str(e)}")
    
    @log_performance(threshold_ms=500)
    async def update_by_field(
        self,
        field: str,
        value: Any,
        data: Dict[str, Any],
        commit: bool = True
    ) -> Optional[ModelType]:
        """
        Update a record by field value.
        
        Args:
            field: Field name
            value: Field value
            data: Dictionary of field values to update
            commit: Whether to commit immediately
        
        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get_by_field(field, value)
        if not instance:
            return None
        
        return await self.update(instance.id, data, commit)
    
    @log_performance(threshold_ms=500)
    async def delete(
        self,
        id: UUID,
        hard_delete: bool = False,
        commit: bool = True
    ) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            hard_delete: If True, permanently delete from database
            commit: Whether to commit immediately
        
        Returns:
            True if deleted successfully
        
        Raises:
            NotFoundError: If record not found
        """
        try:
            if hard_delete:
                # Hard delete
                query = delete(self.model).where(self.model.id == id)
                result = await self.db.execute(query)
                success = result.rowcount > 0
            else:
                # Soft delete
                instance = await self.get_or_raise(id)
                instance.is_active = False
                if hasattr(instance, 'deleted_at'):
                    instance.deleted_at = datetime.utcnow()
                success = True
            
            if commit:
                await self.db.commit()
            
            self.logger.debug(f"Deleted {self.model.__name__}: {id}")
            return success
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to delete record: {str(e)}")
    
    @log_performance(threshold_ms=500)
    async def restore(
        self,
        id: UUID,
        commit: bool = True
    ) -> ModelType:
        """
        Restore a soft-deleted record.
        
        Args:
            id: Record ID
            commit: Whether to commit immediately
        
        Returns:
            Restored model instance
        
        Raises:
            NotFoundError: If record not found
        """
        try:
            instance = await self.get(id, include_deleted=True)
            if not instance:
                raise NotFoundError(
                    f"{self.model.__name__} with id {id} not found"
                )
            
            instance.is_active = True
            if hasattr(instance, 'deleted_at'):
                instance.deleted_at = None
            
            if commit:
                await self.db.commit()
                await self.db.refresh(instance)
            else:
                await self.db.flush()
            
            self.logger.debug(f"Restored {self.model.__name__}: {id}")
            return instance
            
        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to restore {self.model.__name__} {id}: {str(e)}")
            raise DatabaseError(f"Failed to restore record: {str(e)}")
    
    # ==================== LIST OPERATIONS ====================
    
    @log_performance(threshold_ms=500)
    async def list(
        self,
        pagination: Optional[PaginationParams] = None,
        filters: Optional[FilterParams] = None,
        load_relations: Optional[List[str]] = None,
        **kwargs
    ) -> PaginatedResponse[ModelType]:
        """
        List records with pagination and filtering.
        
        Args:
            pagination: Pagination parameters
            filters: Filter parameters
            load_relations: List of relationship names to eager load
            **kwargs: Additional filter conditions (field=value)
        
        Returns:
            Paginated response with records
        """
        pagination = pagination or PaginationParams()
        filters = filters or FilterParams()
        
        # Build query
        query = self._build_list_query(filters, **kwargs)
        query = self._apply_relations(query, load_relations)
        
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
        load_relations: Optional[List[str]] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[ModelType]:
        """
        List all records without pagination.
        
        Args:
            filters: Filter parameters
            load_relations: List of relationship names to eager load
            limit: Maximum number of records to return
            **kwargs: Additional filter conditions
        
        Returns:
            List of records
        """
        filters = filters or FilterParams()
        
        # Build query
        query = self._build_list_query(filters, **kwargs)
        query = self._apply_relations(query, load_relations)
        query = query.where(self.model.is_active == True)
        query = self._apply_sorting(
            query,
            PaginationParams(sort_by='created_at', sort_order='desc')
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    @log_performance(threshold_ms=500)
    async def list_by_ids(
        self,
        ids: List[UUID],
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> List[ModelType]:
        """
        List records by multiple IDs.
        
        Args:
            ids: List of record IDs
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
        
        Returns:
            List of records
        """
        if not ids:
            return []
        
        query = self._build_base_query(include_deleted)
        query = self._apply_relations(query, load_relations)
        query = query.where(self.model.id.in_(ids))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ==================== COUNT OPERATIONS ====================
    
    @log_performance(threshold_ms=500)
    async def count(
        self,
        filters: Optional[FilterParams] = None,
        include_deleted: bool = False,
        **kwargs
    ) -> int:
        """
        Count records matching filters.
        
        Args:
            filters: Filter parameters
            include_deleted: Whether to include soft-deleted records
            **kwargs: Additional filter conditions
        
        Returns:
            Total count
        """
        filters = filters or FilterParams()
        
        query = self._build_count_query(filters, **kwargs)
        if not include_deleted:
            query = query.where(self.model.is_active == True)
        
        return await self._get_count(query)
    
    @log_performance(threshold_ms=500)
    async def exists(
        self,
        filters: Optional[FilterParams] = None,
        include_deleted: bool = False,
        **kwargs
    ) -> bool:
        """
        Check if any records match filters.
        
        Args:
            filters: Filter parameters
            include_deleted: Whether to include soft-deleted records
            **kwargs: Additional filter conditions
        
        Returns:
            True if records exist
        """
        count = await self.count(filters, include_deleted, **kwargs)
        return count > 0
    
    @log_performance(threshold_ms=500)
    async def exists_by_field(
        self,
        field: str,
        value: Any,
        exclude_id: Optional[UUID] = None,
        include_deleted: bool = False
    ) -> bool:
        """
        Check if a record exists with given field value.
        
        Args:
            field: Field name
            value: Field value
            exclude_id: ID to exclude from check
            include_deleted: Whether to include soft-deleted records
        
        Returns:
            True if record exists
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field '{field}' does not exist on {self.model.__name__}")
        
        query = self._build_base_query(include_deleted)
        query = query.where(getattr(self.model, field) == value)
        
        if exclude_id:
            query = query.where(self.model.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    # ==================== BULK OPERATIONS ====================
    
    @log_performance(threshold_ms=1000)
    async def bulk_create(
        self,
        items: List[Dict[str, Any]],
        commit: bool = True
    ) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            items: List of dictionaries with field values
            commit: Whether to commit immediately
        
        Returns:
            List of created model instances
        """
        if not items:
            return []
        
        try:
            instances = []
            for data in items:
                instance = self.model(**data)
                self.db.add(instance)
                instances.append(instance)
            
            if commit:
                await self.db.commit()
                for instance in instances:
                    await self.db.refresh(instance)
            else:
                await self.db.flush()
            
            self.logger.debug(f"Bulk created {len(instances)} {self.model.__name__}")
            return instances
            
        except Exception as e:
            self.logger.error(f"Failed to bulk create {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to bulk create records: {str(e)}")
    
    @log_performance(threshold_ms=1000)
    async def bulk_update(
        self,
        updates: List[Dict[str, Any]],
        id_field: str = 'id',
        commit: bool = True
    ) -> List[ModelType]:
        """
        Update multiple records in bulk.
        
        Args:
            updates: List of dictionaries with id and fields to update
            id_field: Field name for the ID
            commit: Whether to commit immediately
        
        Returns:
            List of updated model instances
        """
        if not updates:
            return []
        
        try:
            instances = []
            for data in updates:
                id_value = data.pop(id_field)
                instance = await self.get_or_raise(id_value)
                
                for key, value in data.items():
                    if hasattr(instance, key) and key not in ['id', 'created_at', 'created_by']:
                        setattr(instance, key, value)
                
                instances.append(instance)
            
            if commit:
                await self.db.commit()
                for instance in instances:
                    await self.db.refresh(instance)
            
            self.logger.debug(f"Bulk updated {len(instances)} {self.model.__name__}")
            return instances
            
        except Exception as e:
            self.logger.error(f"Failed to bulk update {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to bulk update records: {str(e)}")
    
    @log_performance(threshold_ms=1000)
    async def bulk_delete(
        self,
        ids: List[UUID],
        hard_delete: bool = False,
        commit: bool = True
    ) -> int:
        """
        Delete multiple records in bulk.
        
        Args:
            ids: List of record IDs
            hard_delete: If True, permanently delete from database
            commit: Whether to commit immediately
        
        Returns:
            Number of records deleted
        """
        if not ids:
            return 0
        
        try:
            if hard_delete:
                query = delete(self.model).where(self.model.id.in_(ids))
                result = await self.db.execute(query)
                count = result.rowcount
            else:
                # Soft delete
                query = update(self.model).where(
                    self.model.id.in_(ids)
                ).values(
                    is_active=False,
                    deleted_at=datetime.utcnow()
                )
                result = await self.db.execute(query)
                count = result.rowcount
            
            if commit:
                await self.db.commit()
            
            self.logger.debug(f"Bulk deleted {count} {self.model.__name__}")
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to bulk delete {self.model.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to bulk delete records: {str(e)}")
    
    # ==================== QUERY BUILDERS ====================
    
    def _build_base_query(
        self,
        include_deleted: bool = False
    ) -> Select:
        """Build base query"""
        query = select(self.model)
        if not include_deleted:
            query = query.where(self.model.is_active == True)
        return query
    
    def _apply_relations(
        self,
        query: Select,
        relations: Optional[List[str]]
    ) -> Select:
        """Apply eager loading for relationships"""
        if not relations:
            return query
        
        for relation in relations:
            if hasattr(self.model, relation):
                query = query.options(selectinload(getattr(self.model, relation)))
            else:
                self.logger.warning(f"Relation '{relation}' not found on {self.model.__name__}")
        
        return query
    
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
    
    def _build_filter_condition(
        self,
        filter_cond: FilterCondition
    ) -> Optional[Any]:
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
            return column.in_(value) if value else None
        elif operator == FilterOperator.NOT_IN:
            return column.not_in(value) if value else None
        elif operator == FilterOperator.BETWEEN:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return column.between(value[0], value[1])
            return None
        elif operator == FilterOperator.IS_NULL:
            return column.is_(None)
        elif operator == FilterOperator.IS_NOT_NULL:
            return column.is_not(None)
        
        return None
    
    def _apply_sorting(
        self,
        query: Select,
        pagination: PaginationParams
    ) -> Select:
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
    
    # ==================== ADVANCED QUERIES ====================
    
    @log_performance(threshold_ms=500)
    async def find_by_fields(
        self,
        fields: Dict[str, Any],
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[ModelType]:
        """
        Find records by multiple field values (AND condition).
        
        Args:
            fields: Dictionary of field=value conditions
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
            limit: Maximum number of records to return
        
        Returns:
            List of records
        """
        query = self._build_base_query(include_deleted)
        query = self._apply_relations(query, load_relations)
        
        conditions = []
        for field, value in fields.items():
            if hasattr(self.model, field):
                conditions.append(getattr(self.model, field) == value)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    @log_performance(threshold_ms=500)
    async def find_or_create(
        self,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[ModelType, bool]:
        """
        Find a record or create it if not exists.
        
        Args:
            defaults: Default values for creation
            **kwargs: Search conditions and creation values
        
        Returns:
            (instance, created) tuple
        """
        instance = await self.get_by_field(
            field=list(kwargs.keys())[0],
            value=list(kwargs.values())[0],
            include_deleted=False
        )
        
        if instance:
            return instance, False
        
        # Create new instance
        create_data = kwargs.copy()
        if defaults:
            create_data.update(defaults)
        
        instance = await self.create(create_data)
        return instance, True
    
    @log_performance(threshold_ms=500)
    async def get_latest(
        self,
        field: str = 'created_at',
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> Optional[ModelType]:
        """
        Get the latest record.
        
        Args:
            field: Field to determine latest
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
        
        Returns:
            Latest record or None
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field '{field}' does not exist on {self.model.__name__}")
        
        query = self._build_base_query(include_deleted)
        query = self._apply_relations(query, load_relations)
        query = query.order_by(getattr(self.model, field).desc()).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    @log_performance(threshold_ms=500)
    async def get_oldest(
        self,
        field: str = 'created_at',
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> Optional[ModelType]:
        """
        Get the oldest record.
        
        Args:
            field: Field to determine oldest
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
        
        Returns:
            Oldest record or None
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field '{field}' does not exist on {self.model.__name__}")
        
        query = self._build_base_query(include_deleted)
        query = self._apply_relations(query, load_relations)
        query = query.order_by(getattr(self.model, field).asc()).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # ==================== TRANSACTION HELPERS ====================
    
    async def begin_transaction(self):
        """Begin a transaction"""
        await self.db.begin()
    
    async def commit_transaction(self):
        """Commit the current transaction"""
        await self.db.commit()
    
    async def rollback_transaction(self):
        """Rollback the current transaction"""
        await self.db.rollback()
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions"""
        try:
            await self.begin_transaction()
            yield
            await self.commit_transaction()
        except Exception:
            await self.rollback_transaction()
            raise

# ==================== EXPORTS ====================

__all__ = [
    'BaseRepository',
]