"""
Celery tasks for async processing
Background tasks for AI operations, notifications, and scheduling
"""

from app.tasks.celery_app import celery_app
from app.tasks.voice_tasks import process_voice_async, process_conversation_async
from app.tasks.notification_tasks import send_sms_async, send_appointment_reminder_async
from app.tasks.calendar_tasks import schedule_appointment_async, sync_calendar_async

__all__ = [
    "celery_app",
    "process_voice_async",
    "process_conversation_async", 
    "send_sms_async",
    "send_appointment_reminder_async",
    "schedule_appointment_async",
    "sync_calendar_async"
]