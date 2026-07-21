# app/background/jobs/base_job.py
"""
Base job class for background tasks.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_manager
from app.core.logging import get_logger, LogContext
from app.core.cache import cache_manager

logger = get_logger(__name__)

# ==================== BASE JOB ====================

class BaseJob:
    """Base class for all background jobs"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"job.{name}")
        self._session: Optional[AsyncSession] = None
    
    async def execute(self, *args, **kwargs):
        """
        Execute the job.
        Override this method in child classes.
        """
        raise NotImplementedError("Job must implement execute()")
    
    async def run(self, *args, **kwargs):
        """
        Run the job with logging and error handling.
        """
        job_id = kwargs.get('job_id', f"{self.name}_{datetime.utcnow().timestamp()}")
        
        with LogContext(correlation_id=job_id):
            self.logger.info(f"Starting job: {self.name}")
            start_time = datetime.utcnow()
            
            try:
                # Initialize database if needed
                if not db_manager.is_initialized:
                    await db_manager.initialize()
                
                # Initialize cache if needed
                if settings.CACHE_ENABLED and not cache_manager.is_available():
                    await cache_manager.initialize()
                
                # Execute job
                result = await self.execute(*args, **kwargs)
                
                # Log success
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.logger.info(
                    f"Job completed: {self.name} (duration: {duration:.2f}s)",
                    extra={'duration': duration, 'job_id': job_id}
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.logger.error(
                    f"Job failed: {self.name} - {str(e)}",
                    extra={
                        'duration': duration,
                        'job_id': job_id,
                        'error': str(e)
                    },
                    exc_info=True
                )
                raise
            
            finally:
                # Clean up
                if self._session:
                    await self._session.close()
                    self._session = None
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        if not self._session:
            self._session = db_manager.session_factory()
        return self._session
    
    async def get_cache(self):
        """Get cache manager"""
        return cache_manager

# ==================== EXPORTS ====================

__all__ = [
    'BaseJob',
]