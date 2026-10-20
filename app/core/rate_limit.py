"""Sliding-window rate limiter with bounded memory.

Single-process only. Swap for Redis when scaling horizontally.
"""

from __future__ import annotations

import time
from collections import OrderedDict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.request_id import get_request_id

MAX_BUCKETS = 10_000
CLEANUP_INTERVAL_SECONDS = 60
WINDOW_SECONDS = 60

EXEMPT_PREFIXES = ("/static/", "/favicon", "/media/")
EXEMPT_PATHS = {"/health", "/healthz", "/readyz"}


class _Bucket:
    __slots__ = ("hits",)

    def __init__(self) -> None:
        self.hits: deque[float] = deque()


class InMemoryRateLimiter:
    def __init__(self, max_buckets: int = MAX_BUCKETS) -> None:
        self._buckets: OrderedDict[str, _Bucket] = OrderedDict()
        self._max_buckets = max_buckets
        self._last_cleanup = time.monotonic()

    def _cleanup_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_cleanup < CLEANUP_INTERVAL_SECONDS:
            return
        self._last_cleanup = now
        cutoff = now - WINDOW_SECONDS
        stale_keys = [
            k for k, b in self._buckets.items()
            if not b.hits or b.hits[-1] < cutoff
        ]
        for k in stale_keys:
            self._buckets.pop(k, None)

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        self._cleanup_if_due()
        now = time.monotonic()
        cutoff = now - window_seconds

        bucket = self._buckets.get(key)
        if bucket is None:
            while len(self._buckets) >= self._max_buckets:
                self._buckets.popitem(last=False)
            bucket = _Bucket()
            self._buckets[key] = bucket
        else:
            self._buckets.move_to_end(key)

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

        ip = self._client_ip(request)
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
        path = request.url.path
        return path in EXEMPT_PATHS or any(path.startswith(p) for p in EXEMPT_PREFIXES)

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Resolve the real client IP, honoring XFF only when trusted."""
        if settings.TRUST_PROXY_HEADERS:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                first = xff.split(",", 1)[0].strip()
                if first:
                    return first
            xreal = request.headers.get("x-real-ip")
            if xreal:
                return xreal.strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _bucket_for(request: Request, ip: str) -> tuple[int, int, str]:
        path = request.url.path
        if path == "/api/v1/auth/login":
            return settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60, f"login:{ip}"
        if path.startswith("/api/"):
            return settings.RATE_LIMIT_API_PER_MINUTE, 60, f"api:{ip}"
        return settings.RATE_LIMIT_PUBLIC_PER_MINUTE, 60, f"public:{ip}"