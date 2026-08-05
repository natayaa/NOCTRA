# app/background/jobs/cleanup_jobs.py
"""
Cleanup jobs for removing expired/deleted data.
"""

from datetime import datetime, timedelta
from sqlalchemy import delete, and_, or_
from sqlalchemy.sql import func

from app.background.jobs.base_job import BaseJob
from app.core.logging import get_logger
from app.core.database import db_manager

logger = get_logger(__name__)

# ==================== CLEANUP JOBS ====================

class CleanupExpiredTokensJob(BaseJob):
    """Clean up expired JWT tokens"""
    
    def __init__(self):
        super().__init__("cleanup_expired_tokens")
    
    async def execute(self, **kwargs):
        session = await self.get_session()
        
        # Delete expired tokens from blacklist
        # Assuming you have a TokenBlacklist model
        try:
            # Example - adjust based on your model
            from app.modules.auth.models import TokenBlacklist
            
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            result = await session.execute(
                delete(TokenBlacklist).where(
                    TokenBlacklist.expires_at < cutoff
                )
            )
            
            await session.commit()
            count = result.rowcount
            
            logger.info(f"Deleted {count} expired tokens")
            return {'deleted_count': count}
            
        except ImportError:
            # TokenBlacklist model not found
            logger.warning("TokenBlacklist model not found, skipping cleanup")
            return {'deleted_count': 0}

class CleanupOrphanedFilesJob(BaseJob):
    """Clean up orphaned uploaded files"""
    
    def __init__(self):
        super().__init__("cleanup_orphaned_files")
    
    async def execute(self, **kwargs):
        import os
        import shutil
        from pathlib import Path
        
        storage_path = settings.LOCAL_STORAGE_PATH
        temp_path = os.path.join(storage_path, "temp")
        
        deleted_count = 0
        deleted_size = 0
        
        # Clean up temp files older than 24 hours
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            for file_path in Path(temp_path).glob("*"):
                if file_path.is_file():
                    # Check file age
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        deleted_size += size
            
            logger.info(f"Deleted {deleted_count} orphaned files ({deleted_size / 1024 / 1024:.2f} MB)")
            return {
                'deleted_count': deleted_count,
                'deleted_size_mb': deleted_size / 1024 / 1024
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned files: {str(e)}")
            raise

class CleanupOldLogsJob(BaseJob):
    """Clean up old log files"""
    
    def __init__(self):
        super().__init__("cleanup_old_logs")
    
    async def execute(self, **kwargs):
        import os
        from pathlib import Path
        
        log_dir = Path("logs")
        deleted_count = 0
        deleted_size = 0
        
        # Keep only last 30 days of logs
        try:
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            for file_path in log_dir.glob("*.log*"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        deleted_size += size
            
            logger.info(f"Deleted {deleted_count} old log files ({deleted_size / 1024 / 1024:.2f} MB)")
            return {
                'deleted_count': deleted_count,
                'deleted_size_mb': deleted_size / 1024 / 1024
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {str(e)}")
            raise

class CleanupInactiveSessionsJob(BaseJob):
    """Clean up inactive user sessions"""
    
    def __init__(self):
        super().__init__("cleanup_inactive_sessions")
    
    async def execute(self, **kwargs):
        session = await self.get_session()
        
        try:
            from app.modules.auth.models import UserSession
            
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            result = await session.execute(
                delete(UserSession).where(
                    or_(
                        UserSession.last_activity < cutoff,
                        and_(
                            UserSession.is_active == False,
                            UserSession.updated_at < cutoff
                        )
                    )
                )
            )
            
            await session.commit()
            count = result.rowcount
            
            logger.info(f"Deleted {count} inactive sessions")
            return {'deleted_count': count}
            
        except ImportError:
            logger.warning("UserSession model not found, skipping cleanup")
            return {'deleted_count': 0}

# ==================== JOB INSTANCES ====================

cleanup_expired_tokens_job = CleanupExpiredTokensJob()
cleanup_orphaned_files_job = CleanupOrphanedFilesJob()
cleanup_old_logs_job = CleanupOldLogsJob()
cleanup_inactive_sessions_job = CleanupInactiveSessionsJob()

# ==================== WRAPPER FUNCTIONS ====================

async def cleanup_expired_tokens(**kwargs):
    return await cleanup_expired_tokens_job.run(**kwargs)

async def cleanup_orphaned_files(**kwargs):
    return await cleanup_orphaned_files_job.run(**kwargs)

async def cleanup_old_logs(**kwargs):
    return await cleanup_old_logs_job.run(**kwargs)

async def cleanup_inactive_sessions(**kwargs):
    return await cleanup_inactive_sessions_job.run(**kwargs)

# ==================== EXPORTS ====================

__all__ = [
    'cleanup_expired_tokens',
    'cleanup_orphaned_files',
    'cleanup_old_logs',
    'cleanup_inactive_sessions',
]