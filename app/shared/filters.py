# app/shared/filters.py
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.constants import FilterOperators
from app.core.dependencies import FilterParams as CoreFilterParams

# ==================== FILTER OPERATORS ====================

class FilterOperator:
    """Filter operators for query building"""
    
    # Re-export from core
    EQUALS = FilterOperators.EQUALS
    NOT_EQUALS = FilterOperators.NOT_EQUALS
    CONTAINS = FilterOperators.CONTAINS
    STARTS_WITH = FilterOperators.STARTS_WITH
    ENDS_WITH = FilterOperators.ENDS_WITH
    GREATER_THAN = FilterOperators.GREATER_THAN
    GREATER_THAN_OR_EQUAL = FilterOperators.GREATER_THAN_OR_EQUAL
    LESS_THAN = FilterOperators.LESS_THAN
    LESS_THAN_OR_EQUAL = FilterOperators.LESS_THAN_OR_EQUAL
    IN = FilterOperators.IN
    NOT_IN = FilterOperators.NOT_IN
    BETWEEN = FilterOperators.BETWEEN
    IS_NULL = FilterOperators.IS_NULL
    IS_NOT_NULL = FilterOperators.IS_NOT_NULL
    
    @classmethod
    def is_comparison(cls, operator: str) -> bool:
        """Check if operator is a comparison operator"""
        comparison_ops = [
            cls.EQUALS, cls.NOT_EQUALS,
            cls.GREATER_THAN, cls.GREATER_THAN_OR_EQUAL,
            cls.LESS_THAN, cls.LESS_THAN_OR_EQUAL,
        ]
        return operator in comparison_ops
    
    @classmethod
    def is_string_operator(cls, operator: str) -> bool:
        """Check if operator is a string operator"""
        string_ops = [
            cls.CONTAINS, cls.STARTS_WITH, cls.ENDS_WITH
        ]
        return operator in string_ops
    
    @classmethod
    def is_list_operator(cls, operator: str) -> bool:
        """Check if operator is a list operator"""
        list_ops = [
            cls.IN, cls.NOT_IN
        ]
        return operator in list_ops
    
    @classmethod
    def is_null_operator(cls, operator: str) -> bool:
        """Check if operator is a null operator"""
        null_ops = [
            cls.IS_NULL, cls.IS_NOT_NULL
        ]
        return operator in null_ops

# ==================== FILTER CONDITION ====================

class FilterCondition(BaseModel):
    """Single filter condition"""
    
    field: str = Field(..., description="Field name to filter on")
    operator: str = Field(..., description="Filter operator")
    value: Optional[Any] = Field(None, description="Filter value")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'field': self.field,
            'operator': self.operator,
            'value': self.value,
        }

# ==================== FILTER PARAMS ====================

class FilterParams(CoreFilterParams):
    """
    Extended filter parameters with advanced filtering.
    """
    
    def __init__(
        self,
        status: Optional[Union[str, List[str]]] = None,
        category: Optional[Union[str, List[str]]] = None,
        tags: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        created_by: Optional[str] = None,
        custom_filters: Optional[List[FilterCondition]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ):
        super().__init__(status, category, tags, is_active, created_by)
        self.custom_filters = custom_filters or []
        self.date_from = date_from
        self.date_to = date_to
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()
        data['custom_filters'] = [f.to_dict() for f in self.custom_filters]
        data['date_from'] = self.date_from.isoformat() if self.date_from else None
        data['date_to'] = self.date_to.isoformat() if self.date_to else None
        return data
    
    def get_custom_filter(self, field: str) -> Optional[FilterCondition]:
        """Get custom filter by field name"""
        for filter_cond in self.custom_filters:
            if filter_cond.field == field:
                return filter_cond
        return None
    
    def has_filter(self, field: str) -> bool:
        """Check if field has a filter"""
        return self.get_custom_filter(field) is not None

# ==================== EXPORTS ====================

__all__ = [
    'FilterOperator',
    'FilterCondition',
    'FilterParams',
]