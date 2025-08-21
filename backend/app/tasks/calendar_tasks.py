"""
Calendar tasks for Celery
Async tasks for appointment scheduling and calendar sync
"""

import asyncio
from typing import Dict, List
from datetime import datetime, timezone
import structlog

from app.tasks.celery_app import celery_app
from app.services.calendar_service import CalendarService
from app.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="schedule_appointment_async",
    max_retries=3,
    default_retry_delay=60,
    queue="calendar"
)
def schedule_appointment_async(
    self,
    tenant_id: str,
    appointment_data: Dict
):
    """
    Schedule appointment in calendar asynchronously
    
    Args:
        self: Celery task instance
        tenant_id: Tenant ID
        appointment_data: Appointment details
        
    Returns:
        Dict with scheduling results
    """
    try:
        logger.info(
            "Scheduling appointment async",
            task_id=self.request.id,
            tenant_id=tenant_id,
            appointment_type=appointment_data.get("appointment_type", "Unknown")
        )
        
        # Run async scheduling
        result = asyncio.run(_schedule_appointment_internal(
            tenant_id=tenant_id,
            appointment_data=appointment_data,
            task_id=self.request.id
        ))
        
        return result
        
    except Exception as e:
        logger.error(
            "Appointment scheduling failed",
            task_id=self.request.id,
            error=str(e),
            tenant_id=tenant_id
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay * (2 ** self.request.retries))
        
        return {
            "success": False,
            "error": str(e),
            "task_id": self.request.id
        }


@celery_app.task(
    bind=True,
    name="sync_calendar_async",
    max_retries=2,
    default_retry_delay=300,
    queue="calendar"
)
def sync_calendar_async(self, tenant_id: str):
    """
    Sync tenant calendar with external calendar service
    
    Args:
        self: Celery task instance
        tenant_id: Tenant ID to sync
        
    Returns:
        Dict with sync results
    """
    try:
        logger.info("Starting calendar sync", task_id=self.request.id, tenant_id=tenant_id)
        
        # Run async sync
        result = asyncio.run(_sync_tenant_calendar_internal(
            tenant_id=tenant_id,
            task_id=self.request.id
        ))
        
        return result
        
    except Exception as e:
        logger.error("Calendar sync failed", task_id=self.request.id, error=str(e))
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay)
        
        return {
            "success": False,
            "error": str(e),
            "task_id": self.request.id
        }


@celery_app.task(
    bind=True,
    name="sync_all_tenant_calendars",
    queue="calendar"
)
def sync_all_tenant_calendars(self):
    """
    Sync all tenant calendars (periodic task)
    """
    try:
        logger.info("Starting all tenant calendar sync", task_id=self.request.id)
        
        # Run async processing
        result = asyncio.run(_sync_all_calendars_internal(self.request.id))
        
        return result
        
    except Exception as e:
        logger.error("All tenant calendar sync failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "synced": 0,
            "failed": 1
        }


# Internal async functions

async def _schedule_appointment_internal(
    tenant_id: str,
    appointment_data: Dict,
    task_id: str
) -> Dict:
    """Internal appointment scheduling function"""
    
    calendar_service = CalendarService()
    
    try:
        # Parse appointment datetime
        appointment_datetime = datetime.fromisoformat(
            appointment_data["appointment_datetime"].replace('Z', '+00:00')
        )
        
        # Schedule in calendar
        result = await calendar_service.schedule_appointment(
            tenant_id=tenant_id,
            appointment_datetime=appointment_datetime,
            duration_minutes=appointment_data.get("duration_minutes", 30),
            patient_name=appointment_data.get("patient_name", "Unknown"),
            patient_phone=appointment_data.get("patient_phone"),
            appointment_type=appointment_data.get("appointment_type", "Appointment"),
            notes=appointment_data.get("notes")
        )
        
        result["task_id"] = task_id
        return result
        
    except Exception as e:
        logger.error("Internal appointment scheduling failed", error=str(e))
        raise


async def _sync_tenant_calendar_internal(tenant_id: str, task_id: str) -> Dict:
    """Internal calendar sync function"""
    
    # Mock calendar sync - in production this would sync with Google Calendar
    try:
        logger.info("Syncing tenant calendar", tenant_id=tenant_id, task_id=task_id)
        
        # Simulate sync operations
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "events_synced": 5,
            "conflicts_resolved": 0,
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error("Internal calendar sync failed", error=str(e))
        raise


async def _sync_all_calendars_internal(task_id: str) -> Dict:
    """Internal function to sync all tenant calendars"""
    
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            from app.models.tenant import Tenant
            
            # Get all active tenants
            result = await db.execute(select(Tenant).where(Tenant.active == True))
            tenants = result.scalars().all()
            
            synced = 0
            failed = 0
            
            for tenant in tenants:
                try:
                    # Queue individual sync tasks
                    sync_calendar_async.delay(tenant.id)
                    synced += 1
                except Exception as e:
                    logger.error("Failed to queue calendar sync", error=str(e), tenant_id=tenant.id)
                    failed += 1
            
            return {
                "success": failed == 0,
                "synced": synced,
                "failed": failed,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error("Failed to sync all calendars", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "synced": 0,
                "failed": 1
            }