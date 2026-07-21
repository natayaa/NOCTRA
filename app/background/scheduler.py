# app/background/scheduler.py
"""
Scheduler for periodic tasks using APScheduler.
Alternative to Celery Beat for lightweight scheduling.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from datetime import datetime
import asyncio

from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)

# ==================== SCHEDULER CONFIG ====================

class SchedulerManager:
    """Manager for APScheduler"""
    
    _instance = None
    _scheduler: Optional[AsyncIOScheduler] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._jobs = {}
        
        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 60,
        }
        
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.TIMEZONE
        )
        
        # Add event listeners
        self._scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        logger.info("Scheduler manager initialized")
    
    async def start(self):
        """Start the scheduler"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def add_cron_job(
        self,
        func,
        name: str,
        cron: str,
        args: tuple = (),
        kwargs: dict = None,
        **options
    ):
        """
        Add a cron job.
        
        Args:
            func: Async function to execute
            name: Job name
            cron: Cron expression (e.g., "0 2 * * *")
            args: Positional arguments
            kwargs: Keyword arguments
            **options: Additional APScheduler options
        """
        if not kwargs:
            kwargs = {}
        
        job = self._scheduler.add_job(
            func,
            trigger=CronTrigger.from_crontab(cron),
            id=name,
            name=name,
            args=args,
            kwargs=kwargs,
            replace_existing=True,
            **options
        )
        
        self._jobs[name] = job
        logger.info(f"Added cron job: {name} with schedule: {cron}")
        return job
    
    def add_interval_job(
        self,
        func,
        name: str,
        seconds: int = None,
        minutes: int = None,
        hours: int = None,
        args: tuple = (),
        kwargs: dict = None,
        **options
    ):
        """
        Add an interval job.
        
        Args:
            func: Async function to execute
            name: Job name
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours
            args: Positional arguments
            kwargs: Keyword arguments
            **options: Additional APScheduler options
        """
        if not kwargs:
            kwargs = {}
        
        # Determine interval
        if seconds:
            interval = seconds
        elif minutes:
            interval = minutes * 60
        elif hours:
            interval = hours * 3600
        else:
            interval = 60  # Default to 60 seconds
        
        job = self._scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=interval),
            id=name,
            name=name,
            args=args,
            kwargs=kwargs,
            replace_existing=True,
            **options
        )
        
        self._jobs[name] = job
        logger.info(f"Added interval job: {name} with interval: {interval}s")
        return job
    
    def remove_job(self, name: str):
        """Remove a job"""
        if name in self._jobs:
            self._scheduler.remove_job(name)
            del self._jobs[name]
            logger.info(f"Removed job: {name}")
            return True
        return False
    
    def get_job(self, name: str):
        """Get a job by name"""
        return self._jobs.get(name)
    
    def get_all_jobs(self):
        """Get all jobs"""
        return list(self._jobs.values())
    
    def pause_job(self, name: str):
        """Pause a job"""
        if name in self._jobs:
            self._scheduler.pause_job(name)
            logger.info(f"Paused job: {name}")
            return True
        return False
    
    def resume_job(self, name: str):
        """Resume a job"""
        if name in self._jobs:
            self._scheduler.resume_job(name)
            logger.info(f"Resumed job: {name}")
            return True
        return False
    
    async def _job_executed_listener(self, event):
        """Listener for job execution events"""
        if event.exception:
            logger.error(
                f"Job {event.job_id} failed: {event.exception}",
                extra={
                    'job_id': event.job_id,
                    'error': str(event.exception)
                }
            )
        else:
            logger.debug(f"Job {event.job_id} executed successfully")

# ==================== SINGLETON INSTANCE ====================

scheduler_manager = SchedulerManager()

# ==================== EXPORTS ====================

__all__ = [
    'scheduler_manager',
    'SchedulerManager',
]