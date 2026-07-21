# app/background/celery.py
"""
Celery configuration for background tasks.

Usage:
    celery -A app.background.celery worker --loglevel=info
    celery -A app.background.celery beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready, worker_shutdown
from app.core.config import settings
from app.core.logging import get_logger
import asyncio
import os

logger = get_logger(__name__)

# ==================== CELERY APP ====================

# Create Celery app
celery_app = Celery(
    "noktra",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/1",
    backend=settings.CELERY_RESULT_BACKEND or "redis://localhost:6379/2",
    include=[
        "app.background.jobs.email_jobs",
        "app.background.jobs.report_jobs",
        "app.background.jobs.cleanup_jobs",
        "app.background.jobs.notification_jobs",
        "app.background.jobs.backup_jobs",
    ]
)

# ==================== CELERY CONFIG ====================

celery_app.conf.update(
    # Task settings
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_max_retries=settings.CELERY_TASK_MAX_RETRIES,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    timezone=settings.TIMEZONE,
    
    # Worker settings
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=200000,  # 200MB
    
    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Logging
    worker_redirect_stdouts=False,
    worker_redirect_stdouts_level="INFO",
    
    # Beat schedule
    beat_schedule={
        # Cleanup jobs
        "cleanup-expired-tokens": {
            "task": "app.background.jobs.cleanup_jobs.cleanup_expired_tokens",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
            "options": {"expires": 3600},
        },
        "cleanup-orphaned-files": {
            "task": "app.background.jobs.cleanup_jobs.cleanup_orphaned_files",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
            "options": {"expires": 3600},
        },
        "cleanup-old-logs": {
            "task": "app.background.jobs.cleanup_jobs.cleanup_old_logs",
            "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Weekly on Sunday
            "options": {"expires": 3600},
        },
        "cleanup-inactive-sessions": {
            "task": "app.background.jobs.cleanup_jobs.cleanup_inactive_sessions",
            "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
            "options": {"expires": 3600},
        },
        
        # Report jobs
        "generate-daily-report": {
            "task": "app.background.jobs.report_jobs.generate_daily_report",
            "schedule": crontab(hour=23, minute=30),  # Daily at 11:30 PM
            "options": {"expires": 3600},
        },
        "generate-weekly-report": {
            "task": "app.background.jobs.report_jobs.generate_weekly_report",
            "schedule": crontab(hour=23, minute=30, day_of_week=6),  # Saturday at 11:30 PM
            "options": {"expires": 3600},
        },
        "generate-monthly-report": {
            "task": "app.background.jobs.report_jobs.generate_monthly_report",
            "schedule": crontab(hour=23, minute=30, day_of_month=1),  # 1st of month at 11:30 PM
            "options": {"expires": 3600},
        },
        
        # Notification jobs
        "send-pending-reminders": {
            "task": "app.background.jobs.notification_jobs.send_pending_reminders",
            "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM
            "options": {"expires": 3600},
        },
        "send-due-reminders": {
            "task": "app.background.jobs.notification_jobs.send_due_reminders",
            "schedule": crontab(hour=10, minute=0),  # Daily at 10 AM
            "options": {"expires": 3600},
        },
        "send-overdue-notifications": {
            "task": "app.background.jobs.notification_jobs.send_overdue_notifications",
            "schedule": crontab(hour=14, minute=0),  # Daily at 2 PM
            "options": {"expires": 3600},
        },
        "send-low-stock-alerts": {
            "task": "app.background.jobs.notification_jobs.send_low_stock_alerts",
            "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM
            "options": {"expires": 3600},
        },
        
        # Backup jobs
        "backup-database": {
            "task": "app.background.jobs.backup_jobs.backup_database",
            "schedule": crontab(hour=0, minute=0),  # Daily at midnight
            "options": {"expires": 3600},
        },
        "cleanup-old-backups": {
            "task": "app.background.jobs.backup_jobs.cleanup_old_backups",
            "schedule": crontab(hour=1, minute=0, day_of_week=0),  # Weekly on Sunday
            "options": {"expires": 3600},
        },
        
        # Status update jobs
        "update-order-status": {
            "task": "app.background.jobs.status_jobs.update_order_status",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
            "options": {"expires": 300},
        },
        "update-inventory-status": {
            "task": "app.background.jobs.status_jobs.update_inventory_status",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
            "options": {"expires": 300},
        },
        
        # Email jobs
        "send-daily-digest": {
            "task": "app.background.jobs.email_jobs.send_daily_digest",
            "schedule": crontab(hour=7, minute=0),  # Daily at 7 AM
            "options": {"expires": 3600},
        },
        "send-weekly-digest": {
            "task": "app.background.jobs.email_jobs.send_weekly_digest",
            "schedule": crontab(hour=8, minute=0, day_of_week=0),  # Monday at 8 AM
            "options": {"expires": 3600},
        },
    },
)

# ==================== CELERY SIGNALS ====================

@worker_ready.connect
def worker_ready_handler(*args, **kwargs):
    """Handler when worker is ready"""
    logger.info("Celery worker is ready and connected to broker")
    
    # Initialize database connection pool
    from app.core.database import db_manager
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If event loop is running, create task
            asyncio.create_task(db_manager.initialize())
        else:
            # Run synchronously
            loop.run_until_complete(db_manager.initialize())
    except Exception as e:
        logger.error(f"Failed to initialize database for Celery: {str(e)}")

@worker_shutdown.connect
def worker_shutdown_handler(*args, **kwargs):
    """Handler when worker is shutting down"""
    logger.info("Celery worker is shutting down")
    
    # Close database connection
    from app.core.database import db_manager
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(db_manager.close())
        else:
            loop.run_until_complete(db_manager.close())
    except Exception as e:
        logger.error(f"Failed to close database for Celery: {str(e)}")

# ==================== TASK BASE CLASS ====================

class TaskWithDatabase(celery_app.Task):
    """Base task with database session management"""
    
    _db_manager = None
    
    async def get_db(self):
        """Get database session"""
        from app.core.database import db_manager
        
        if not db_manager.is_initialized:
            await db_manager.initialize()
        
        return db_manager
    
    async def get_session(self):
        """Get database session"""
        db = await self.get_db()
        return db.session_factory()
    
    def __call__(self, *args, **kwargs):
        """Execute task with database cleanup"""
        result = super().__call__(*args, **kwargs)
        
        # Clean up session if exists
        if hasattr(self, '_session'):
            asyncio.create_task(self._session.close())
            self._session = None
        
        return result

# ==================== EXPORTS ====================

__all__ = [
    'celery_app',
    'TaskWithDatabase',
]