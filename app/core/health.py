# core/health.py
from typing import Dict, Any
from datetime import datetime
import asyncio

from core.database import check_db_connection
from core.config import settings


class HealthChecker:
    """Health check untuk berbagai komponen."""

    @classmethod
    async def check_database(cls) -> Dict[str, Any]:
        """Check database connection."""
        try:
            is_healthy = await check_db_connection()
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "message": "Database connection successful" if is_healthy else "Database connection failed",
                "details": {"type": "postgresql"}
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e),
                "details": {"type": "postgresql"}
            }

    @classmethod
    async def check_redis(cls) -> Dict[str, Any]:
        """Check Redis connection."""
        # Implementasi Redis check jika menggunakan Redis
        return {
            "status": "healthy",
            "message": "Redis not configured",
            "details": {"type": "redis", "configured": False}
        }

    @classmethod
    async def check_storage(cls) -> Dict[str, Any]:
        """Check storage availability."""
        try:
            import os
            upload_dir = settings.UPLOAD_DIR
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # Test write
            test_file = os.path.join(upload_dir, ".health_check")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)

            return {
                "status": "healthy",
                "message": "Storage is writable",
                "details": {"path": upload_dir}
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e),
                "details": {"path": settings.UPLOAD_DIR}
            }

    @classmethod
    async def run_checks(cls) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "checks": {}
        }

        # Run checks concurrently
        checks = await asyncio.gather(
            cls.check_database(),
            cls.check_redis(),
            cls.check_storage(),
        )

        results["checks"]["database"] = checks[0]
        results["checks"]["redis"] = checks[1]
        results["checks"]["storage"] = checks[2]

        # Determine overall status
        for check in checks:
            if check["status"] != "healthy":
                results["status"] = "degraded"
                break

        return results
