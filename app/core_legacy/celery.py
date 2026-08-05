# core/celery.py
from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "workshop",
    broker=settings.REDIS_URL or "redis://localhost:6379/0",
    backend=settings.REDIS_URL or "redis://localhost:6379/0",
    include=[
        "tasks.notification",
        "tasks.report",
        "tasks.reminder",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    "send-daily-reminders": {
        "task": "tasks.reminder.send_daily_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    "update-overdue-status": {
        "task": "tasks.reminder.update_overdue_status",
        "schedule": crontab(hour=0, minute=0),
    },
    "generate-daily-report": {
        "task": "tasks.report.generate_daily_report",
        "schedule": crontab(hour=23, minute=59),
    },
}
