# app/background/jobs/backup_jobs.py
"""
Backup jobs for database and files.
"""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import zipfile

from app.background.jobs.base_job import BaseJob
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# ==================== BACKUP JOBS ====================

class BackupDatabaseJob(BaseJob):
    """Backup the database"""
    
    def __init__(self):
        super().__init__("backup_database")
    
    async def execute(self, **kwargs):
        backup_dir = Path("backups/database")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"backup_{timestamp}.sql"
        
        try:
            # PostgreSQL backup using pg_dump
            # This assumes pg_dump is installed and in PATH
            command = [
                "pg_dump",
                f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}",
                "--format=custom",
                "--file", str(backup_file),
                "--verbose"
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            
            if result.returncode != 0:
                logger.error(f"Backup failed: {result.stderr}")
                raise Exception(f"Backup failed: {result.stderr}")
            
            # Compress backup
            zip_file = backup_dir / f"backup_{timestamp}.zip"
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(backup_file, backup_file.name)
            
            # Delete raw backup file
            backup_file.unlink()
            
            file_size = zip_file.stat().st_size / 1024 / 1024
            
            logger.info(f"Database backup created: {zip_file.name} ({file_size:.2f} MB)")
            
            return {
                'filename': str(zip_file.name),
                'size_mb': file_size,
                'timestamp': timestamp
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Database backup timed out")
            raise
        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            raise

class CleanupOldBackupsJob(BaseJob):
    """Clean up old backup files"""
    
    def __init__(self):
        super().__init__("cleanup_old_backups")
    
    async def execute(self, **kwargs):
        backup_dir = Path("backups/database")
        deleted_count = 0
        deleted_size = 0
        
        # Keep only last 7 backups
        try:
            # Get all backup files
            backup_files = sorted(
                backup_dir.glob("backup_*.zip"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # Keep only last 7
            for file_path in backup_files[7:]:
                size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                deleted_size += size
            
            logger.info(f"Deleted {deleted_count} old backups ({deleted_size / 1024 / 1024:.2f} MB)")
            
            return {
                'deleted_count': deleted_count,
                'deleted_size_mb': deleted_size / 1024 / 1024
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {str(e)}")
            raise

# ==================== JOB INSTANCES ====================

backup_database_job = BackupDatabaseJob()
cleanup_old_backups_job = CleanupOldBackupsJob()

# ==================== WRAPPER FUNCTIONS ====================

async def backup_database(**kwargs):
    return await backup_database_job.run(**kwargs)

async def cleanup_old_backups(**kwargs):
    return await cleanup_old_backups_job.run(**kwargs)

# ==================== EXPORTS ====================

__all__ = [
    'backup_database',
    'cleanup_old_backups',
]