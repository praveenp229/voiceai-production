"""
Celery application configuration for VoiceAI 2.0
Handles async task processing for voice operations, notifications, and scheduling
"""

from celery import Celery
from kombu import Queue
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Create Celery app instance
celery_app = Celery(
    "voiceai_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.voice_tasks",
        "app.tasks.notification_tasks", 
        "app.tasks.calendar_tasks",
        "app.tasks.maintenance_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Performance settings
    worker_prefetch_multiplier=1,  # Prevent memory issues
    task_acks_late=True,           # Acknowledge after completion
    worker_disable_rate_limits=False,
    
    # Retry settings
    task_default_retry_delay=60,   # 1 minute
    task_max_retries=3,
    
    # Result backend settings
    result_expires=3600,           # 1 hour
    
    # Queue routing
    task_routes={
        "app.tasks.voice_tasks.*": {"queue": "voice"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.calendar_tasks.*": {"queue": "calendar"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"}
    },
    
    # Queue definitions
    task_queues=(
        Queue("voice", routing_key="voice", priority=9),          # High priority
        Queue("notifications", routing_key="notifications", priority=7), # Medium-high priority  
        Queue("calendar", routing_key="calendar", priority=5),    # Medium priority
        Queue("maintenance", routing_key="maintenance", priority=1), # Low priority
    ),
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,
)

# Custom task base class for logging and error handling
class VoiceAITask(celery_app.Task):
    """Base task class with logging and error handling"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Task success callback"""
        logger.info(
            "Task completed successfully",
            task_id=task_id,
            task_name=self.name,
            result_preview=str(retval)[:100] if retval else None
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Task failure callback"""
        logger.error(
            "Task failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            traceback=str(einfo)
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Task retry callback"""
        logger.warning(
            "Task retrying",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            retry_count=self.request.retries
        )

# Set custom task base class
celery_app.Task = VoiceAITask

# Health check task
@celery_app.task(bind=True, name="health_check")
def health_check_task(self):
    """Health check task to verify Celery is working"""
    return {
        "status": "healthy",
        "worker_id": self.request.id,
        "timestamp": "2025-01-21T00:00:00Z"  # This would be dynamic
    }

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Health check every 5 minutes
    "health-check": {
        "task": "health_check",
        "schedule": 300.0,  # 5 minutes
    },
    
    # Send appointment reminders
    "appointment-reminders": {
        "task": "app.tasks.notification_tasks.send_scheduled_reminders",
        "schedule": 1800.0,  # 30 minutes
    },
    
    # Cleanup old call logs
    "cleanup-old-logs": {
        "task": "app.tasks.maintenance_tasks.cleanup_old_call_logs", 
        "schedule": 86400.0,  # 24 hours
    },
    
    # Sync calendar events
    "sync-calendars": {
        "task": "app.tasks.calendar_tasks.sync_all_tenant_calendars",
        "schedule": 3600.0,  # 1 hour
    },
}

# Configure structured logging for Celery
def setup_celery_logging():
    """Configure Celery to use structured logging"""
    
    # Import here to avoid circular imports
    from app.core.logging import setup_logging
    setup_logging()
    
    logger.info("Celery structured logging configured")

# Initialize logging when module is imported
setup_celery_logging()

logger.info(
    "Celery app configured",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    queues=["voice", "notifications", "calendar", "maintenance"]
)