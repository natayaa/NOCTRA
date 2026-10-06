"""
Simple in-memory sliding-window rate limiter.

Not suitable for multi-process deployments — swap for Redis
when you scale beyond a single instance.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.request_id import get_request_id


class _Bucket:
    __slots__ = ("lock", "hits")

    def __init__(self) -> None:
        self.lock = Lock()
        self.hits: deque[float] = deque()


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = defaultdict(_Bucket)

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket = self._buckets[key]
        with bucket.lock:
            while bucket.hits and bucket.hits[0] < cutoff:
                bucket.hits.popleft()
            if len(bucket.hits) >= limit:
                retry = int(window_seconds - (now - bucket.hits[0]))
                return False, max(1, retry)
            bucket.hits.append(now)
            return True, 0


limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED or self._is_exempt(request):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        limit, window, key = self._bucket_for(request, ip)
        allowed, retry_after = limiter.hit(key, limit, window)
        if not allowed:
            return JSONResponse(
                {
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests",
                        "request_id": get_request_id(),
                    }
                },
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    @staticmethod
    def _is_exempt(request: Request) -> bool:
        return request.url.path.startswith("/static/")

    @staticmethod
    def _bucket_for(request: Request, ip: str) -> tuple[int, int, str]:
        path = request.url.path
        if path == "/api/v1/auth/login":
            return settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60, f"login:{ip}"
        if path.startswith("/api/"):
            return settings.RATE_LIMIT_API_PER_MINUTE, 60, f"api:{ip}"
        return settings.RATE_LIMIT_PUBLIC_PER_MINUTE, 60, f"public:{ip}"