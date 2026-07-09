# core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from typing import Dict, Any
import time


# =============================================================================
# Metrics
# =============================================================================

# Request metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

# Business metrics
projects_total = Gauge(
    "projects_total",
    "Total number of projects",
    ["status"]
)

inquiries_total = Gauge(
    "inquiries_total",
    "Total number of inquiries",
    ["status"]
)

payments_total = Counter(
    "payments_total_amount",
    "Total payment amount",
    ["type"]
)


# =============================================================================
# Metrics Middleware
# =============================================================================

class MetricsMiddleware:
    """Middleware untuk mengumpulkan metrics."""

    async def __call__(self, request, call_next):
        method = request.method
        path = request.url.path

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Record metrics
        request_count.labels(
            method=method,
            endpoint=path,
            status_code=response.status_code
        ).inc()

        request_duration.labels(
            method=method,
            endpoint=path
        ).observe(duration)

        return response


# =============================================================================
# Metrics Endpoint
# =============================================================================

async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")
