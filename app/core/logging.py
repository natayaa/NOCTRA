# core/logging.py - FIXED
import logging
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json
import os

from core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter untuk structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(
    log_level: Optional[str] = None,
    json_format: bool = True,
    log_file: Optional[str] = None
) -> None:
    """Setup logging configuration."""

    # ✅ Gunakan dari settings atau parameter
    level = log_level or getattr(settings, 'LOG_LEVEL', 'INFO')
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        # Buat folder logs jika belum ada
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10_485_760,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    # Set SQLAlchemy logging
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.WARNING)

    # Set uvicorn logging
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)


# =============================================================================
# Audit Logger
# =============================================================================

class AuditLogger:
    """Logger untuk audit trail."""

    def __init__(self, db_session=None):
        self.db = db_session
        self.logger = get_logger("audit")

    def log(
        self,
        action: str,
        resource: str,
        resource_id: str,
        user_id: Optional[str] = None,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log audit event."""
        self.logger.info(
            f"Audit: {action} on {resource} {resource_id}",
            extra={
                "extra": {
                    "audit": True,
                    "action": action,
                    "resource": resource,
                    "resource_id": resource_id,
                    "user_id": user_id,
                    "changes": changes,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                }
            }
        )


# ✅ AUTO-INIT ketika di-import
setup_logging()
