# core/health.py - FIXED
from typing import Dict, Any
from datetime import datetime
import asyncio
import os

from core.database import check_db_connection
from core.config import settings
from core.logging import get_logger

logger = get_logger("health")


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
            logger.error(f"Database check error: {e}")
            return {
                "status": "unhealthy",
                "message": str(e),
                "details": {"type": "postgresql"}
            }

    @classmethod
    async def check_redis(cls) -> Dict[str, Any]:
        """Check Redis connection."""
        try:
            # Cek apakah Redis dikonfigurasi
            if not settings.REDIS_URL:
                return {
                    "status": "healthy",
                    "message": "Redis not configured",
                    "details": {"type": "redis", "configured": False}
                }

            # Coba konek ke Redis
            import redis.asyncio as redis
            client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await client.ping()
            await client.close()

            return {
                "status": "healthy",
                "message": "Redis connection successful",
                "details": {"type": "redis", "configured": True}
            }
        except ImportError:
            return {
                "status": "healthy",
                "message": "Redis not installed",
                "details": {"type": "redis", "configured": False}
            }
        except Exception as e:
            logger.error(f"Redis check error: {e}")
            return {
                "status": "unhealthy",
                "message": str(e),
                "details": {"type": "redis", "configured": True}
            }

    @classmethod
    async def check_storage(cls) -> Dict[str, Any]:
        """Check storage availability."""
        try:
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
            logger.error(f"Storage check error: {e}")
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
            return_exceptions=True
        )

        results["checks"]["database"] = checks[0] if not isinstance(
            checks[0], Exception) else {"status": "unhealthy", "message": str(checks[0])}
        results["checks"]["redis"] = checks[1] if not isinstance(
            checks[1], Exception) else {"status": "unhealthy", "message": str(checks[1])}
        results["checks"]["storage"] = checks[2] if not isinstance(
            checks[2], Exception) else {"status": "unhealthy", "message": str(checks[2])}

        # Determine overall status
        for key, check in results["checks"].items():
            if check.get("status") != "healthy":
                results["status"] = "degraded"
                break

        return results
