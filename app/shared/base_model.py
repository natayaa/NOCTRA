# app/shared/base_model.py
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import Column, DateTime, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base
import uuid

from core.database import Base as CoreBase
from core.constants import DateTimeConstants

# ==================== BASE MODEL ====================

class BaseModel(CoreBase):
    """
    Abstract base model with common fields and methods.
    All models should inherit from this class.
    """
    
    __abstract__ = True
    
    # Common fields
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Primary key UUID"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Soft delete flag"
    )
    created_at = Column(
        DateTime,
        default=func.now(),
        nullable=False,
        doc="Creation timestamp"
    )
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Last update timestamp"
    )
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        doc="User ID who created this record"
    )
    updated_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="User ID who last updated this record"
    )
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name"""
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        # Handle pluralization for common words
        if not name.endswith('s'):
            if name.endswith('y'):
                name = name[:-1] + 'ies'
            elif name.endswith('x') or name.endswith('s') or name.endswith('ch') or name.endswith('sh'):
                name = name + 'es'
            else:
                name = name + 's'
        return name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            result[column.name] = value
        return result
    
    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return self.to_dict()
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update model with dictionary data"""
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'created_at', 'created_by']:
                setattr(self, key, value)
    
    def soft_delete(self) -> None:
        """Soft delete the record"""
        self.is_active = False
    
    def restore(self) -> None:
        """Restore soft-deleted record"""
        self.is_active = True
    
    @classmethod
    def get_fields(cls) -> list:
        """Get all field names"""
        return [column.name for column in cls.__table__.columns]
    
    @classmethod
    def get_required_fields(cls) -> list:
        """Get required (non-nullable) field names"""
        return [
            column.name for column in cls.__table__.columns
            if not column.nullable and column.name not in ['id', 'created_at', 'updated_at']
        ]
    
    @classmethod
    def get_filterable_fields(cls) -> list:
        """Get fields that can be used for filtering"""
        return cls.get_fields()

# ==================== EXPORTS ====================

__all__ = [
    'BaseModel',
]