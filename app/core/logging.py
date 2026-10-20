import logging
import sys

import structlog

from app.core.config import settings
from app.core.request_id import get_request_id

SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "csrf", "authorization"}
_MAX_REDACT_DEPTH = 5
_CONFIGURED = False


def _redact(obj, depth: int = 0):
    """Recursively redact sensitive keys inside nested dicts/lists."""
    if depth > _MAX_REDACT_DEPTH:
        return obj
    if isinstance(obj, dict):
        return {
            k: (
                "***"
                if any(s in str(k).lower() for s in SENSITIVE_KEYS)
                else _redact(v, depth + 1)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return type(obj)(_redact(v, depth + 1) for v in obj)
    return obj


def _redact_sensitive(_, __, event_dict: dict) -> dict:
    return _redact(event_dict)


def _add_request_id(_, __, event_dict: dict) -> dict:
    rid = get_request_id()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:              # idempotent — safe to call twice (e.g. tests)
        return
    _CONFIGURED = True

    level = getattr(logging, settings.APP_LOG_LEVEL)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        _redact_sensitive,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.APP_LOG_FORMAT == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


log = structlog.get_logger()