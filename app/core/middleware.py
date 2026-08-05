import time
import uuid

from typing import Optional, List, Tuple, Dict, Any
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi.responses import JSONResponse

from .config import settings
from .logging import logger, request_id_var
from .exceptions import ErrorResponseFormatter

# ==================== REQUEST ID MIDDLEWARE ====================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure every request has a unique ID.
    Uses X-Request-ID header or generates one.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Set in context
        request_id_var.set(request_id)
        
        # Add to request state for access in endpoints
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response

# ==================== CORS MIDDLEWARE ====================

class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware with configurable origins, methods, and headers.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, request)
            return response
        
        # Process actual request
        response = await call_next(request)
        self._add_cors_headers(response, request)
        return response
    
    def _add_cors_headers(self, response: Response, request: Request):
        """Add CORS headers to response"""
        origin = request.headers.get("origin")
        
        # Check if origin is allowed
        if "*" in settings.CORS_ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin and origin in settings.CORS_ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Add other CORS headers
        response.headers["Access-Control-Allow-Methods"] = ", ".join(settings.CORS_ALLOW_METHODS)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(settings.CORS_ALLOW_HEADERS)
        response.headers["Access-Control-Expose-Headers"] = ", ".join(settings.CORS_EXPOSE_HEADERS)
        response.headers["Access-Control-Max-Age"] = str(settings.CORS_MAX_AGE)

# ==================== RATE LIMIT MIDDLEWARE ====================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using in-memory or Redis storage.
    """
    
    def __init__(self, app: ASGIApp, requests_per_period: int = None, period_seconds: int = None, skip_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.requests_per_period = requests_per_period or settings.RATE_LIMIT_DEFAULT_REQUESTS
        self.period_seconds = period_seconds or settings.RATE_LIMIT_DEFAULT_PERIOD
        self.skip_paths = skip_paths or [
            "/health", "/docs", "/redoc", "/openapi.json"
        ]
        
        # In-memory store (for development, use Redis in production)
        self._store: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        identifier = f"{client_ip}:{request.url.path}"
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_rate_limit(identifier)
        
        if not is_allowed:
            return ErrorResponseFormatter.to_json_response(
                message="Rate limit exceeded",
                code="RATE_LIMIT_EXCEEDED",
                status_code=429,
                details={
                    "retry_after": reset_time,
                    "limit": self.requests_per_period
                },
                request_id=request.state.request_id if hasattr(request.state, "request_id") else None,
                path=str(request.url.path),
                method=request.method
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_period)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit(self, identifier: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed.
        Returns: (is_allowed, remaining_requests, reset_time)
        """
        now = int(time.time())
        
        # Try Redis first if available
        try:
            from app.core.cache import cache_manager
            if cache_manager.is_available():
                return await self._check_redis_rate_limit(identifier, now)
        except ImportError:
            pass
        
        # Fallback to in-memory
        return await self._check_memory_rate_limit(identifier, now)
    
    async def _check_redis_rate_limit(self, identifier: str, now: int) -> Tuple[bool, int, int]:
        """Check rate limit using Redis"""
        from app.core.cache import cache_manager
        
        key = f"ratelimit:{identifier}"
        
        # Get current count
        current = await cache_manager.get(key)
        
        if current is None:
            # First request
            await cache_manager.set(key, 1, self.period_seconds)
            return True, self.requests_per_period - 1, now + self.period_seconds
        
        # Increment counter
        new_count = await cache_manager.increment(key)
        
        # Check if limit exceeded
        if new_count > self.requests_per_period:
            # Get TTL
            ttl = await cache_manager._redis_client.ttl(key)
            return False, 0, int(time.time() + ttl) if ttl > 0 else now + self.period_seconds
        
        remaining = self.requests_per_period - new_count
        return True, remaining, now + self.period_seconds
    
    async def _check_memory_rate_limit(self, identifier: str, now: int) -> Tuple[bool, int, int]:
        """Check rate limit using in-memory store"""
        if identifier not in self._store:
            # First request
            self._store[identifier] = {
                "count": 1,
                "window_start": now,
                "window_end": now + self.period_seconds
            }
            return True, self.requests_per_period - 1, now + self.period_seconds
        
        data = self._store[identifier]
        
        # Check if window has expired
        if now > data["window_end"]:
            # Reset window
            data["count"] = 1
            data["window_start"] = now
            data["window_end"] = now + self.period_seconds
            return True, self.requests_per_period - 1, now + self.period_seconds
        
        # Increment count
        data["count"] += 1
        
        # Check if limit exceeded
        if data["count"] > self.requests_per_period:
            reset_time = data["window_end"]
            return False, 0, reset_time
        
        remaining = self.requests_per_period - data["count"]
        return True, remaining, data["window_end"]

# ==================== LOGGING MIDDLEWARE ====================

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all requests and responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get request ID from state
        request_id = request.state.request_id if hasattr(request.state, "request_id") else None
        
        # Start timer
        start_time = time.time()
        
        # Log request
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
        }
        
        logger.info(f"Request: {request.method} {request.url.path}", extra=log_data)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            log_response = {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "method": request.method,
                "path": request.url.path,
            }
            
            if duration_ms > 1000:  # > 1 second
                logger.warning(f"Slow request: {duration_ms:.2f}ms", extra=log_response)
            else:
                logger.info(f"Response: {response.status_code}", extra=log_response)
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "duration_ms": round(duration_ms, 2),
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                }
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

# ==================== RESPONSE TIME MIDDLEWARE ====================

class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add response time header.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        response_time = (time.time() - start_time) * 1000
        response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
        return response

# ==================== SECURITY HEADERS MIDDLEWARE ====================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        if settings.SECURE_SSL_REDIRECT:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.SECURE_HSTS_SECONDS}"
                f"{'; includeSubDomains' if settings.SECURE_HSTS_INCLUDE_SUBDOMAINS else ''}"
            )
        
        if settings.SECURE_FRAME_DENY:
            response.headers["X-Frame-Options"] = "DENY"
        
        if settings.SECURE_CONTENT_TYPE_NOSNIFF:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        if settings.SECURE_XSS_PROTECTION:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        
        response.headers["Referrer-Policy"] = settings.SECURE_REFERRER_POLICY
        
        if settings.SECURE_CSP:
            response.headers["Content-Security-Policy"] = settings.SECURE_CSP
        
        return response

# ==================== REQUEST SIZE MIDDLEWARE ====================

class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request size.
    """
    
    MAX_SIZE = 10 * 1024 * 1024  # 10MB default
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_SIZE:
            return ErrorResponseFormatter.to_json_response(
                message="Request too large",
                code="REQUEST_TOO_LARGE",
                status_code=413,
                details={
                    "max_size": f"{self.MAX_SIZE / (1024 * 1024):.0f}MB"
                },
                request_id=request.state.request_id if hasattr(request.state, "request_id") else None,
                path=str(request.url.path),
                method=request.method
            )
        
        return await call_next(request)

# ==================== SETUP FUNCTION ====================

def setup_middleware(app: FastAPI) -> None:
    """
    Setup all middleware for the application.
    Order matters: first added, first executed.
    """
    
    # 1. Request ID (should be first)
    app.add_middleware(RequestIDMiddleware)
    
    # 2. Request size limit
    app.add_middleware(RequestSizeMiddleware)
    
    # 3. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 4. CORS
    app.add_middleware(CORSMiddleware)
    
    # 5. Rate limiting
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)
    
    # 6. Response time
    app.add_middleware(ResponseTimeMiddleware)
    
    # 7. Logging (should be last to capture everything)
    app.add_middleware(LoggingMiddleware)
    
    logger.info("Middleware setup complete")

# ==================== EXPORTS ====================

__all__ = [
    "setup_middleware",
    "RequestIDMiddleware",
    "CORSMiddleware",
    "RateLimitMiddleware",
    "LoggingMiddleware",
    "ResponseTimeMiddleware",
    "SecurityHeadersMiddleware",
    "RequestSizeMiddleware",
]