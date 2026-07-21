# app/shared/__init__.py
"""
Shared components for NOKTRA Autoworks Dashboard.
"""

from app.shared.base_model import BaseModel
from app.shared.base_services import BaseService
from app.shared.enums import (
    BaseEnum,
    Gender,
    Status,
    Priority,
    DayOfWeek,
    Month,
    YesNo,
    TrueFalse,
)
from app.shared.filters import (
    FilterOperator,
    FilterCondition,
    FilterParams,
)
from app.shared.pagination import (
    PaginationParams,
    PaginatedResponse,
)
from app.shared.responses import (
    BaseResponse,
    SuccessResponse,
    ListResponse,
    ErrorResponse,
    ErrorDetail,
    ResponseBuilder,
)
from app.shared.validators import (
    Validator,
    ValidationMixin,
)
from app.shared.utils import (
    generate_uuid,
    generate_short_id,
    generate_order_number,
    now,
    format_date,
    format_datetime,
    parse_date,
    get_date_range,
    slugify,
    truncate_text,
    camel_to_snake,
    snake_to_camel,
    round_decimal,
    format_currency,
    parse_currency,
    to_json,
    get_file_extension,
    get_file_size_str,
)

__all__ = [
    # Base Model
    'BaseModel',
    
    # Base Service
    'BaseService',
    
    'BaseRepository',
    
    # Enums
    'BaseEnum',
    'Gender',
    'Status',
    'Priority',
    'DayOfWeek',
    'Month',
    'YesNo',
    'TrueFalse',
    
    # Filters
    'FilterOperator',
    'FilterCondition',
    'FilterParams',
    
    # Pagination
    'PaginationParams',
    'PaginatedResponse',
    
    # Responses
    'BaseResponse',
    'SuccessResponse',
    'ListResponse',
    'ErrorResponse',
    'ErrorDetail',
    'ResponseBuilder',
    
    # Validator
    'Validator',
    'ValidationMixin',
    
    # Utils
    'generate_uuid',
    'generate_short_id',
    'generate_order_number',
    'now',
    'format_date',
    'format_datetime',
    'parse_date',
    'get_date_range',
    'slugify',
    'truncate_text',
    'camel_to_snake',
    'snake_to_camel',
    'round_decimal',
    'format_currency',
    'parse_currency',
    'to_json',
    'get_file_extension',
    'get_file_size_str',
]