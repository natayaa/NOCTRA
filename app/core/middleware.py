# core/middleware.py
import time
import uuid
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logging import get_logger
from core.config import settings

logger = get_logger("middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware untuk menambahkan Request ID ke setiap request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware untuk logging request/response."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "extra": {
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "request_id": getattr(request.state, "request_id", None),
                }
            }
        )

        try:
            response = await call_next(request)

            # Log response
            duration = (time.time() - start_time) * 1000
            logger.info(
                f"Response: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "extra": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration, 2),
                        "request_id": getattr(request.state, "request_id", None),
                    }
                }
            )

            return response

        except Exception as e:
            logger.error(
                f"Error: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "extra": {
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(e),
                        "request_id": getattr(request.state, "request_id", None),
                    }
                }
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware untuk rate limiting (sederhana)."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        # Simple in-memory cache (gunakan Redis untuk production)
        self.cache = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Skip rate limit untuk health check
        if path == "/health":
            return await call_next(request)

        key = f"{client_ip}:{path}"
        current_time = time.time()

        # Clean old entries
        self.cache = {k: v for k, v in self.cache.items() if v >
                      current_time - 60}

        if key in self.cache:
            return Response(
                content='{"success": false, "message": "Too many requests"}',
                status_code=429,
                media_type="application/json"
            )

        self.cache[key] = current_time

        return await call_next(request)
