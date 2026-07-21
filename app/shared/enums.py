# app/shared/enums.py
from enum import Enum, IntEnum
from typing import List, Dict, Any

# ==================== BASE ENUM ====================

class BaseEnum(str, Enum):
    """Base enum with utility methods"""
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all enum values"""
        return [item.value for item in cls]
    
    @classmethod
    def names(cls) -> List[str]:
        """Get all enum names"""
        return [item.name for item in cls]
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert enum to dictionary"""
        return {item.name: item.value for item in cls}
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is valid enum value"""
        return value in cls.values()
    
    @classmethod
    def get(cls, value: str, default=None):
        """Get enum by value with fallback"""
        for item in cls:
            if item.value == value:
                return item
        return default

# ==================== COMMON ENUMS ====================

class Gender(BaseEnum):
    """Gender enum"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Status(BaseEnum):
    """Generic status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DELETED = "deleted"

class Priority(BaseEnum):
    """Priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class DayOfWeek(BaseEnum):
    """Days of the week"""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class Month(BaseEnum):
    """Months of the year"""
    JANUARY = "january"
    FEBRUARY = "february"
    MARCH = "march"
    APRIL = "april"
    MAY = "may"
    JUNE = "june"
    JULY = "july"
    AUGUST = "august"
    SEPTEMBER = "september"
    OCTOBER = "october"
    NOVEMBER = "november"
    DECEMBER = "december"

class YesNo(BaseEnum):
    """Yes/No enum"""
    YES = "yes"
    NO = "no"

class TrueFalse(BaseEnum):
    """True/False enum"""
    TRUE = "true"
    FALSE = "false"

# ==================== EXPORTS ====================

__all__ = [
    'BaseEnum',
    'Gender',
    'Status',
    'Priority',
    'DayOfWeek',
    'Month',
    'YesNo',
    'TrueFalse',
]