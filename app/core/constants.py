# app/core/constants.py
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import timedelta

# ==================== HTTP & API CONSTANTS ====================

class HTTPStatus:
    """HTTP status codes with descriptions"""
    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # 3xx Redirection
    MOVED_PERMANENTLY = 301
    FOUND = 302
    NOT_MODIFIED = 304
    
    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

class APIConstants:
    """General API constants"""
    # Pagination
    DEFAULT_PAGE = 1
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100
    MIN_LIMIT = 1
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_PERIOD = 60  # seconds
    
    # Headers
    HEADER_REQUEST_ID = "X-Request-ID"
    HEADER_API_VERSION = "X-API-Version"
    HEADER_RATE_LIMIT_LIMIT = "X-RateLimit-Limit"
    HEADER_RATE_LIMIT_REMAINING = "X-RateLimit-Remaining"
    HEADER_RATE_LIMIT_RESET = "X-RateLimit-Reset"
    HEADER_RESPONSE_TIME = "X-Response-Time"
    
    # API Version
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"
    
    # Query Parameters
    QUERY_PAGE = "page"
    QUERY_LIMIT = "limit"
    QUERY_SORT_BY = "sort_by"
    QUERY_SORT_ORDER = "sort_order"
    QUERY_SEARCH = "search"
    QUERY_FILTERS = "filters"

# ==================== REGEX PATTERNS ====================

class RegexPatterns:
    """Common regex patterns for validation"""
    # General
    UUID = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PHONE = r'^\+?[0-9]{8,15}$'
    URL = r'^https?://[^\s/$.?#].[^\s]*$'
    
    # Indonesia specific
    PHONE_INDONESIA = r'^\+?62[0-9]{9,13}$'
    PLATE_NUMBER = r'^[A-Z]{1,2}\s?[0-9]{1,4}\s?[A-Z]{1,3}$'
    NIK = r'^[0-9]{16}$'  # Indonesian ID card
    NPWP = r'^[0-9]{15}$'  # Indonesian tax ID
    
    # General    PASSWORD = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    ALPHANUMERIC = r'^[a-zA-Z0-9]+$'
    ALPHANUMERIC_SPACE = r'^[a-zA-Z0-9 ]+$'
    NAME = r'^[a-zA-Z\s\-\.]+$'

# ==================== DATE/TIME CONSTANTS ====================

class DateTimeConstants:
    """Date and time format constants"""
    # Format strings
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    TIME_FORMAT = "%H:%M:%S"
    DATETIME_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    DATE_READABLE = "%d %B %Y"
    DATETIME_READABLE = "%d %B %Y %H:%M"
    
    # Timezone
    TIMEZONE_DEFAULT = "Asia/Jakarta"
    TIMEZONE_UTC = "UTC"
    
    # Common durations (in seconds)
    ONE_MINUTE = 60
    FIVE_MINUTES = 300
    ONE_HOUR = 3600
    ONE_DAY = 86400
    ONE_WEEK = 604800
    ONE_MONTH = 2592000  # 30 days
    ONE_YEAR = 31536000  # 365 days
    
    # Cache TTLs (in seconds)
    CACHE_TTL = {
        "SHORT": 60,          # 1 minute
        "MEDIUM": 300,        # 5 minutes
        "LONG": 3600,         # 1 hour
        "VERY_LONG": 86400,   # 24 hours
        "FOREVER": 31536000   # 1 year
    }

# ==================== FILE CONSTANTS ====================

class FileConstants:
    """File upload and management constants"""
    # Max file sizes (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024     # 10MB
    MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024    # 100MB
    MAX_GENERAL_SIZE = 50 * 1024 * 1024   # 50MB
    
    # Allowed extensions
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', 
        '.webp', '.bmp', '.svg', '.ico'
    }
    DOCUMENT_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', 
        '.xlsx', '.ppt', '.pptx', '.txt', 
        '.csv', '.rtf'
    }
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mov', '.wmv', 
        '.flv', '.mkv', '.webm'
    }
    AUDIO_EXTENSIONS = {
        '.mp3', '.wav', '.ogg', '.m4a', 
        '.flac', '.aac'
    }
    ARCHIVE_EXTENSIONS = {
        '.zip', '.rar', '.7z', '.tar', 
        '.gz', '.bz2'
    }
    
    # All extensions combined
    ALLOWED_EXTENSIONS = (
        IMAGE_EXTENSIONS | 
        DOCUMENT_EXTENSIONS | 
        VIDEO_EXTENSIONS | 
        AUDIO_EXTENSIONS | 
        ARCHIVE_EXTENSIONS
    )
    
    # Upload directory structure
    UPLOAD_DIRS = {
        "TEMP": "temp",
        "IMAGES": "images",
        "DOCUMENTS": "documents",
        "ATTACHMENTS": "attachments",
        "EXPORTS": "exports",
        "IMPORTS": "imports"
    }
    
    # MIME types mapping
    MIME_TYPES = {
        # Images
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        # Documents
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        # Videos
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        # Archives
        '.zip': 'application/zip',
        '.rar': 'application/vnd.rar',
        '.7z': 'application/x-7z-compressed',
    }

# ==================== MESSAGE CONSTANTS ====================

class Messages:
    """Standard message templates"""
    
    class Success:
        CREATED = "Resource created successfully"
        UPDATED = "Resource updated successfully"
        DELETED = "Resource deleted successfully"
        FETCHED = "Resource fetched successfully"
        STATUS_CHANGED = "Status changed successfully"
        UPLOADED = "File uploaded successfully"
        EXPORTED = "Data exported successfully"
        IMPORTED = "Data imported successfully"
        SENT = "Sent successfully"
        VERIFIED = "Verified successfully"
        APPROVED = "Approved successfully"
        REJECTED = "Rejected successfully"
        CANCELLED = "Cancelled successfully"
        COMPLETED = "Completed successfully"
    
    class Error:
        NOT_FOUND = "Resource not found"
        DUPLICATE = "Duplicate entry found"
        INVALID_INPUT = "Invalid input provided"
        UNAUTHORIZED = "Authentication required"
        FORBIDDEN = "Permission denied"
        BAD_REQUEST = "Bad request"
        INTERNAL_ERROR = "Internal server error"
        SERVICE_UNAVAILABLE = "Service unavailable"
        TIMEOUT = "Request timeout"
        VALIDATION_ERROR = "Validation error"
        DATABASE_ERROR = "Database error"
        CONFLICT = "Resource conflict"
        RATE_LIMIT = "Rate limit exceeded"
        INVALID_CREDENTIALS = "Invalid credentials"
        EXPIRED_TOKEN = "Token expired"
        INVALID_TOKEN = "Invalid token"
        MISSING_REQUIRED = "Required field missing"
        INVALID_FILE = "Invalid file format"
        FILE_TOO_LARGE = "File too large"
        STORAGE_ERROR = "Storage error"
        INVALID_OPERATION = "Invalid operation"
        DEPENDENCY_ERROR = "Dependency error"
    
    class Validation:
        REQUIRED = "{field} is required"
        INVALID = "{field} is invalid"
        MIN_LENGTH = "{field} must be at least {min} characters"
        MAX_LENGTH = "{field} must be at most {max} characters"
        MIN_VALUE = "{field} must be at least {min}"
        MAX_VALUE = "{field} must be at most {max}"
        INVALID_EMAIL = "Invalid email format"
        INVALID_PHONE = "Invalid phone number format"
        INVALID_UUID = "Invalid UUID format"
        INVALID_DATE = "Invalid date format"
        INVALID_URL = "Invalid URL format"
        PASSWORDS_DONT_MATCH = "Passwords don't match"
        ALREADY_EXISTS = "{field} already exists"

# ==================== CACHE KEYS ====================

class CacheKeys:
    """Cache key patterns for different modules"""
    
    # Base patterns (to be used by modules)
    USER = "user:{user_id}"
    USER_SESSION = "user:{user_id}:session"
    USER_PERMISSIONS = "user:{user_id}:permissions"
    USER_ROLES = "user:{user_id}:roles"
    
    # These are just patterns - modules will implement their own
    # using these patterns as base
    MODULE_PREFIXES = {
        "auth": "auth",
        "user": "user",
        "order": "order",
        "inventory": "inventory",
        "customer": "customer",
        "payment": "payment",
        "report": "report",
        "settings": "settings",
        "workshop": "workshop",
    }

# ==================== SORT ORDER ====================

class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value.lower() in [cls.ASC.value, cls.DESC.value]

class FilterOperators:
    """Filter operators for query building"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    STARTS_WITH = "sw"
    ENDS_WITH = "ew"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "nin"
    BETWEEN = "between"
    IS_NULL = "isnull"
    IS_NOT_NULL = "isnotnull"

# ==================== LOGGING ====================

class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# ==================== CORS ====================

class CORSConstants:
    """CORS configuration constants"""
    DEFAULT_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    ALLOW_HEADERS = [
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Request-ID",
        "X-API-Key",
        "X-API-Version",
    ]
    EXPOSE_HEADERS = [
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Response-Time",
    ]

# ==================== RESPONSE FORMAT ====================

class ResponseFields:
    """Standard response field names"""
    SUCCESS = "success"
    DATA = "data"
    ERROR = "error"
    MESSAGE = "message"
    CODE = "code"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    REQUEST_ID = "request_id"
    PAGINATION = "pagination"
    TOTAL = "total"
    PAGE = "page"
    LIMIT = "limit"
    PAGES = "pages"
    ITEMS = "items"

# ==================== EXPORTS ====================

__all__ = [
    # HTTP & API
    'HTTPStatus',
    'APIConstants',
    
    # Validation
    'RegexPatterns',
    
    # Date/Time
    'DateTimeConstants',
    
    # Files
    'FileConstants',
    
    # Messages
    'Messages',
    
    # Cache
    'CacheKeys',
    
    # Sorting & Filtering
    'SortOrder',
    'FilterOperators',
    
    # Logging
    'LogLevel',
    
    # CORS
    'CORSConstants',
    
    # Response
    'ResponseFields',
]