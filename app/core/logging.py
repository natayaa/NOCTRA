# app/core/logging.py
import logging
import sys
import json
import traceback
import uuid
import asyncio
import time

from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from contextvars import ContextVar

from .config import settings
from .constants import Environment

# ==================== CONTEXT VARIABLES ====================

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# ==================== CUSTOM LOGGING FILTERS ====================

class RequestIdFilter(logging.Filter):
    """Add request ID to log records"""
    
    def filter(self, record):
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        record.correlation_id = correlation_id_var.get() or "-"
        return True

# ==================== CUSTOM LOGGING FORMATTERS ====================

class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development"""
    
    COLORS = {
        "DEBUG": "\033[94m",    # Blue
        "INFO": "\033[92m",     # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",    # Red
        "CRITICAL": "\033[95m"  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

# ==================== LOGGER MANAGER ====================

class LoggerManager:
    """Centralized logging management"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Setup root logger with handlers"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self._get_log_level())
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add request ID filter
        root_logger.addFilter(RequestIdFilter())
        
        # Add handlers based on environment
        if settings.APP_ENVIRONMENT in [Environment.DEVELOPMENT, Environment.TESTING]:
            root_logger.addHandler(self._create_console_handler())
        else:
            root_logger.addHandler(self._create_file_handler())
        
        # Always add JSON handler for structured logging
        if settings.LOG_JSON_FORMAT:
            root_logger.addHandler(self._create_json_handler())
        
        # Add error file handler
        root_logger.addHandler(self._create_error_file_handler())
    
    def _get_log_level(self) -> int:
        """Get log level from settings"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(settings.LOG_LEVEL.upper(), logging.INFO)
    
    def _create_console_handler(self) -> logging.Handler:
        """Create console handler with colored output"""
        handler = logging.StreamHandler(sys.stdout)
        
        if settings.APP_ENVIRONMENT == Environment.DEVELOPMENT:
            formatter = ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:
            formatter = logging.Formatter(
                settings.LOG_FORMAT,
                datefmt=settings.LOG_DATE_FORMAT
            )
        
        handler.setFormatter(formatter)
        return handler
    
    def _create_file_handler(self) -> logging.Handler:
        """Create rotating file handler"""
        handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_SIZE,
            backupCount=settings.LOG_BACKUP_COUNT
        )
        
        formatter = logging.Formatter(
            settings.LOG_FORMAT,
            datefmt=settings.LOG_DATE_FORMAT
        )
        handler.setFormatter(formatter)
        return handler
    
    def _create_error_file_handler(self) -> logging.Handler:
        """Create file handler for error logs only"""
        error_log_file = settings.LOG_FILE.replace(".log", "_error.log")
        handler = RotatingFileHandler(
            error_log_file,
            maxBytes=settings.LOG_MAX_SIZE,
            backupCount=settings.LOG_BACKUP_COUNT
        )
        
        formatter = logging.Formatter(
            settings.LOG_FORMAT,
            datefmt=settings.LOG_DATE_FORMAT
        )
        handler.setFormatter(formatter)
        handler.setLevel(logging.ERROR)
        return handler
    
    def _create_json_handler(self) -> logging.Handler:
        """Create JSON formatter handler"""
        json_log_file = settings.LOG_FILE.replace(".log", "_json.log")
        handler = TimedRotatingFileHandler(
            json_log_file,
            when="midnight",
            interval=1,
            backupCount=30
        )
        
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        return handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger instance"""
        logger = logging.getLogger(name)
        logger.propagate = True
        return logger

# ==================== CONTEXT MANAGERS ====================

class LogContext:
    """Context manager for setting logging context"""
    
    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.correlation_id = correlation_id or self.request_id
        
        self._old_request_id = None
        self._old_user_id = None
        self._old_correlation_id = None
    
    def __enter__(self):
        self._old_request_id = request_id_var.get()
        self._old_user_id = user_id_var.get()
        self._old_correlation_id = correlation_id_var.get()
        
        request_id_var.set(self.request_id)
        user_id_var.set(self.user_id)
        correlation_id_var.set(self.correlation_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        request_id_var.set(self._old_request_id)
        user_id_var.set(self._old_user_id)
        correlation_id_var.set(self._old_correlation_id)

# ==================== DECORATORS ====================

def with_log_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None
):
    """Decorator to add log context to a function"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with LogContext(request_id, user_id, correlation_id):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with LogContext(request_id, user_id, correlation_id):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator

def log_performance(threshold_ms: int = 1000):
    """Decorator to log function performance"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = (time.perf_counter() - start) * 1000
                    
                    if elapsed > threshold_ms:
                        logging.getLogger(func.__module__).warning(
                            f"Slow operation: {func.__name__} took {elapsed:.2f}ms"
                        )
                    return result
                except Exception as e:
                    elapsed = (time.perf_counter() - start) * 1000
                    logging.getLogger(func.__module__).error(
                        f"Error in {func.__name__} after {elapsed:.2f}ms: {str(e)}"
                    )
                    raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    elapsed = (time.perf_counter() - start) * 1000
                    
                    if elapsed > threshold_ms:
                        logging.getLogger(func.__module__).warning(
                            f"Slow operation: {func.__name__} took {elapsed:.2f}ms"
                        )
                    return result
                except Exception as e:
                    elapsed = (time.perf_counter() - start) * 1000
                    logging.getLogger(func.__module__).error(
                        f"Error in {func.__name__} after {elapsed:.2f}ms: {str(e)}"
                    )
                    raise
            return sync_wrapper
    return decorator

# ==================== FACTORY FUNCTIONS ====================

logger_manager = LoggerManager()

def get_logger(name: str = "noktra") -> logging.Logger:
    """Get logger instance"""
    return logger_manager.get_logger(name)

# ==================== DEFAULT LOGGER ====================

logger = get_logger("core")

# ==================== SETUP FUNCTION ====================

def setup_logging() -> None:
    """Initialize logging system"""
    logger.info(
        f"Logging initialized for {settings.APP_NAME} v{settings.APP_VERSION}",
        extra={
            "environment": settings.APP_ENVIRONMENT.value,
            "log_level": settings.LOG_LEVEL
        }
    )

# ==================== EXPORTS ====================

__all__ = [
    "get_logger",
    "logger",
    "setup_logging",
    "LogContext",
    "with_log_context",
    "log_performance",
    "request_id_var",
    "user_id_var",
    "correlation_id_var",
]