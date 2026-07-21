# app/background/cron.py
"""
Cron job definitions and registration.
"""

from app.background.scheduler import scheduler_manager
from app.background.jobs import (
    cleanup_jobs,
    report_jobs,
    notification_jobs,
    email_jobs,
    backup_jobs,
    status_jobs,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# ==================== CRON JOB REGISTRATION ====================

def register_cron_jobs():
    """Register all cron jobs"""
    
    # ============ CLEANUP JOBS ============
    
    # Daily at 2 AM - Clean expired tokens
    scheduler_manager.add_cron_job(
        cleanup_jobs.cleanup_expired_tokens,
        name="cleanup_expired_tokens",
        cron="0 2 * * *"
    )
    
    # Daily at 3 AM - Clean orphaned files
    scheduler_manager.add_cron_job(
        cleanup_jobs.cleanup_orphaned_files,
        name="cleanup_orphaned_files",
        cron="0 3 * * *"
    )
    
    # Weekly on Sunday at 4 AM - Clean old logs
    scheduler_manager.add_cron_job(
        cleanup_jobs.cleanup_old_logs,
        name="cleanup_old_logs",
        cron="0 4 * * 0"
    )
    
    # Daily at 1 AM - Clean inactive sessions
    scheduler_manager.add_cron_job(
        cleanup_jobs.cleanup_inactive_sessions,
        name="cleanup_inactive_sessions",
        cron="0 1 * * *"
    )
    
    # ============ REPORT JOBS ============
    
    # Daily at 11:30 PM - Generate daily report
    scheduler_manager.add_cron_job(
        report_jobs.generate_daily_report,
        name="generate_daily_report",
        cron="30 23 * * *"
    )
    
    # Saturday at 11:30 PM - Generate weekly report
    scheduler_manager.add_cron_job(
        report_jobs.generate_weekly_report,
        name="generate_weekly_report",
        cron="30 23 * * 6"
    )
    
    # 1st of month at 11:30 PM - Generate monthly report
    scheduler_manager.add_cron_job(
        report_jobs.generate_monthly_report,
        name="generate_monthly_report",
        cron="30 23 1 * *"
    )
    
    # ============ NOTIFICATION JOBS ============
    
    # Daily at 8 AM - Send pending reminders
    scheduler_manager.add_cron_job(
        notification_jobs.send_pending_reminders,
        name="send_pending_reminders",
        cron="0 8 * * *"
    )
    
    # Daily at 10 AM - Send due reminders
    scheduler_manager.add_cron_job(
        notification_jobs.send_due_reminders,
        name="send_due_reminders",
        cron="0 10 * * *"
    )
    
    # Daily at 2 PM - Send overdue notifications
    scheduler_manager.add_cron_job(
        notification_jobs.send_overdue_notifications,
        name="send_overdue_notifications",
        cron="0 14 * * *"
    )
    
    # Daily at 9 AM - Send low stock alerts
    scheduler_manager.add_cron_job(
        notification_jobs.send_low_stock_alerts,
        name="send_low_stock_alerts",
        cron="0 9 * * *"
    )
    
    # ============ BACKUP JOBS ============
    
    # Daily at midnight - Backup database
    scheduler_manager.add_cron_job(
        backup_jobs.backup_database,
        name="backup_database",
        cron="0 0 * * *"
    )
    
    # Weekly on Sunday at 1 AM - Cleanup old backups
    scheduler_manager.add_cron_job(
        backup_jobs.cleanup_old_backups,
        name="cleanup_old_backups",
        cron="0 1 * * 0"
    )
    
    # ============ STATUS UPDATE JOBS ============
    
    # Every 15 minutes - Update order status
    scheduler_manager.add_interval_job(
        status_jobs.update_order_status,
        name="update_order_status",
        minutes=15
    )
    
    # Every 30 minutes - Update inventory status
    scheduler_manager.add_interval_job(
        status_jobs.update_inventory_status,
        name="update_inventory_status",
        minutes=30
    )
    
    # ============ EMAIL JOBS ============
    
    # Daily at 7 AM - Send daily digest
    scheduler_manager.add_cron_job(
        email_jobs.send_daily_digest,
        name="send_daily_digest",
        cron="0 7 * * *"
    )
    
    # Monday at 8 AM - Send weekly digest
    scheduler_manager.add_cron_job(
        email_jobs.send_weekly_digest,
        name="send_weekly_digest",
        cron="0 8 * * 1"
    )
    
    logger.info("All cron jobs registered")

# ==================== EXPORTS ====================

__all__ = [
    'register_cron_jobs',
]