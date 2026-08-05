# app/shared/utils.py
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
from decimal import Decimal, ROUND_HALF_UP

# ==================== ID GENERATORS ====================

def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid.uuid4())

def generate_short_id(length: int = 8) -> str:
    """Generate short alphanumeric ID"""
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_order_number(prefix: str = "ORD", length: int = 6) -> str:
    """Generate order number with prefix and random digits"""
    import secrets
    digits = ''.join(secrets.choice('0123456789') for _ in range(length))
    return f"{prefix}-{digits}"

# ==================== DATE UTILITIES ====================

def now() -> datetime:
    """Get current UTC datetime"""
    return datetime.utcnow()

def format_date(
    date: datetime,
    format: str = "%Y-%m-%d"
) -> str:
    """Format date to string"""
    return date.strftime(format)

def format_datetime(
    date: datetime,
    format: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """Format datetime to string"""
    return date.strftime(format)

def parse_date(
    date_str: str,
    format: str = "%Y-%m-%d"
) -> datetime:
    """Parse date string to datetime"""
    return datetime.strptime(date_str, format)

def get_date_range(
    period: str
) -> tuple[datetime, datetime]:
    """
    Get date range for a period.
    
    Args:
        period: today, yesterday, week, month, quarter, year
    
    Returns:
        (start_date, end_date)
    """
    now = datetime.utcnow()
    
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now
    
    if period == "yesterday":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end
    
    if period == "week":
        start = now - timedelta(days=7)
        return start, now
    
    if period == "month":
        start = now - timedelta(days=30)
        return start, now
    
    if period == "quarter":
        start = now - timedelta(days=90)
        return start, now
    
    if period == "year":
        start = now - timedelta(days=365)
        return start, now
    
    # Default: last 30 days
    start = now - timedelta(days=30)
    return start, now

# ==================== STRING UTILITIES ====================

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text

def truncate_text(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= length:
        return text
    return text[:length].strip() + suffix

def camel_to_snake(text: str) -> str:
    """Convert camelCase to snake_case"""
    text = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', text).lower()

def snake_to_camel(text: str) -> str:
    """Convert snake_case to camelCase"""
    components = text.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

# ==================== NUMBER UTILITIES ====================

def round_decimal(value: float, places: int = 2) -> float:
    """Round float to specified decimal places"""
    return Decimal(str(value)).quantize(
        Decimal('0.1') ** places,
        rounding=ROUND_HALF_UP
    )

def format_currency(
    value: float,
    currency: str = "Rp",
    decimal_places: int = 0
) -> str:
    """Format currency for display"""
    formatted = f"{currency} "
    if decimal_places > 0:
        formatted += f"{value:,.{decimal_places}f}"
    else:
        formatted += f"{value:,.0f}"
    return formatted.replace(",", ".")

def parse_currency(value: str) -> float:
    """Parse currency string to float"""
    cleaned = re.sub(r'[Rp\s,\.]', '', value)
    cleaned = cleaned.replace(',', '.')
    return float(cleaned)

# ==================== JSON UTILITIES ====================

def to_json(data: Any) -> Dict[str, Any]:
    """Convert data to JSON-serializable dict"""
    if hasattr(data, 'to_dict'):
        return data.to_dict()
    if hasattr(data, 'dict'):
        return data.dict()
    if hasattr(data, 'model_dump'):
        return data.model_dump()
    return data

# ==================== FILE UTILITIES ====================

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

def get_file_size_str(size: int) -> str:
    """Convert file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

# ==================== EXPORTS ====================

__all__ = [
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