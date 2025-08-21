"""
Notification tasks for Celery
Async tasks for SMS, email, and reminder notifications
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from celery import current_task
import structlog

from app.tasks.celery_app import celery_app
from app.services.sms_service import SMSService
from app.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="send_sms_async",
    max_retries=3,
    default_retry_delay=30,
    queue="notifications"
)
def send_sms_async(
    self,
    phone_number: str,
    message: str,
    message_type: str = "general",
    tenant_id: str = None,
    appointment_id: str = None
):
    """
    Send SMS notification asynchronously
    
    Args:
        self: Celery task instance
        phone_number: Recipient phone number
        message: SMS message text
        message_type: Type of message (confirmation, reminder, etc.)
        tenant_id: Tenant ID for logging
        appointment_id: Related appointment ID
        
    Returns:
        Dict with send status and details
    """
    try:
        logger.info(
            "Sending SMS notification",
            task_id=self.request.id,
            phone=f"{phone_number[:3]}***",
            message_type=message_type,
            tenant_id=tenant_id
        )
        
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={"status": f"Sending {message_type} SMS"}
        )
        
        # Send SMS
        sms_service = SMSService()
        result = asyncio.run(sms_service.send_custom_message(
            patient_phone=phone_number,
            message=message
        ))
        
        if result["success"]:
            logger.info(
                "SMS sent successfully",
                task_id=self.request.id,
                message_sid=result.get("message_sid"),
                phone=f"{phone_number[:3]}***"
            )
        else:
            logger.error(
                "SMS sending failed",
                task_id=self.request.id,
                error=result.get("error"),
                phone=f"{phone_number[:3]}***"
            )
        
        # Add task metadata
        result.update({
            "task_id": self.request.id,
            "message_type": message_type,
            "tenant_id": tenant_id,
            "appointment_id": appointment_id
        })
        
        return result
        
    except Exception as e:
        logger.error(
            "SMS task failed",
            task_id=self.request.id,
            error=str(e),
            phone=f"{phone_number[:3]}***"
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            delay = self.default_retry_delay * (2 ** self.request.retries)
            logger.info(f"Retrying SMS send (attempt {self.request.retries + 1}) in {delay}s")
            raise self.retry(countdown=delay)
        
        return {
            "success": False,
            "error": str(e),
            "task_id": self.request.id
        }


@celery_app.task(
    bind=True,
    name="send_appointment_confirmation_async",
    max_retries=3,
    default_retry_delay=30,
    queue="notifications"
)
def send_appointment_confirmation_async(
    self,
    appointment_id: str,
    tenant_id: str,
    patient_phone: str,
    patient_name: str,
    appointment_datetime_iso: str,
    practice_name: str = "our practice"
):
    """
    Send appointment confirmation SMS asynchronously
    
    Args:
        self: Celery task instance
        appointment_id: Appointment ID
        tenant_id: Tenant ID
        patient_phone: Patient phone number
        patient_name: Patient name
        appointment_datetime_iso: Appointment datetime in ISO format
        practice_name: Practice name
        
    Returns:
        Dict with confirmation status
    """
    try:
        logger.info(
            "Sending appointment confirmation",
            task_id=self.request.id,
            appointment_id=appointment_id,
            tenant_id=tenant_id,
            phone=f"{patient_phone[:3]}***"
        )
        
        # Parse datetime
        appointment_datetime = datetime.fromisoformat(appointment_datetime_iso.replace('Z', '+00:00'))
        
        # Send confirmation
        sms_service = SMSService()
        result = asyncio.run(sms_service.send_appointment_confirmation(
            patient_phone=patient_phone,
            patient_name=patient_name,
            appointment_datetime=appointment_datetime,
            practice_name=practice_name
        ))
        
        # Update database with notification status
        if result["success"]:
            await _update_appointment_sms_status(appointment_id, result["message_sid"])
        
        logger.info(
            "Appointment confirmation processed",
            task_id=self.request.id,
            success=result["success"],
            appointment_id=appointment_id
        )
        
        result.update({
            "task_id": self.request.id,
            "appointment_id": appointment_id
        })
        
        return result
        
    except Exception as e:
        logger.error(
            "Appointment confirmation task failed",
            task_id=self.request.id,
            error=str(e),
            appointment_id=appointment_id
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay * (2 ** self.request.retries))
        
        return {
            "success": False,
            "error": str(e),
            "task_id": self.request.id,
            "appointment_id": appointment_id
        }


@celery_app.task(
    bind=True,
    name="send_appointment_reminder_async",
    max_retries=3,
    default_retry_delay=60,
    queue="notifications"
)
def send_appointment_reminder_async(
    self,
    appointment_id: str,
    tenant_id: str,
    patient_phone: str,
    patient_name: str,
    appointment_datetime_iso: str,
    hours_before: int = 24,
    practice_name: str = "our practice"
):
    """
    Send appointment reminder SMS asynchronously
    
    Args:
        self: Celery task instance
        appointment_id: Appointment ID
        tenant_id: Tenant ID
        patient_phone: Patient phone number
        patient_name: Patient name
        appointment_datetime_iso: Appointment datetime in ISO format
        hours_before: Hours before appointment
        practice_name: Practice name
        
    Returns:
        Dict with reminder status
    """
    try:
        logger.info(
            "Sending appointment reminder",
            task_id=self.request.id,
            appointment_id=appointment_id,
            hours_before=hours_before,
            phone=f"{patient_phone[:3]}***"
        )
        
        # Parse datetime
        appointment_datetime = datetime.fromisoformat(appointment_datetime_iso.replace('Z', '+00:00'))
        
        # Check if appointment is still in the future
        if appointment_datetime <= datetime.now(timezone.utc):
            logger.warning(
                "Skipping reminder for past appointment",
                appointment_id=appointment_id,
                appointment_time=appointment_datetime.isoformat()
            )
            return {
                "success": False,
                "error": "Appointment is in the past",
                "appointment_id": appointment_id
            }
        
        # Send reminder
        sms_service = SMSService()
        result = asyncio.run(sms_service.send_appointment_reminder(
            patient_phone=patient_phone,
            patient_name=patient_name,
            appointment_datetime=appointment_datetime,
            practice_name=practice_name,
            hours_before=hours_before
        ))
        
        # Update database with reminder status
        if result["success"]:
            await _update_appointment_reminder_status(appointment_id, hours_before)
        
        logger.info(
            "Appointment reminder processed",
            task_id=self.request.id,
            success=result["success"],
            appointment_id=appointment_id
        )
        
        result.update({
            "task_id": self.request.id,
            "appointment_id": appointment_id,
            "hours_before": hours_before
        })
        
        return result
        
    except Exception as e:
        logger.error(
            "Appointment reminder task failed",
            task_id=self.request.id,
            error=str(e),
            appointment_id=appointment_id
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay * (2 ** self.request.retries))
        
        return {
            "success": False,
            "error": str(e),
            "task_id": self.request.id,
            "appointment_id": appointment_id
        }


@celery_app.task(
    bind=True,
    name="send_scheduled_reminders",
    queue="notifications"
)
def send_scheduled_reminders(self):
    """
    Send scheduled appointment reminders (periodic task)
    Runs every 30 minutes to check for upcoming appointments needing reminders
    """
    try:
        logger.info("Starting scheduled reminder check", task_id=self.request.id)
        
        # Run async reminder processing
        result = asyncio.run(_process_scheduled_reminders(self.request.id))
        
        logger.info(
            "Scheduled reminders processed",
            task_id=self.request.id,
            reminders_sent=result.get("reminders_sent", 0),
            errors=result.get("errors", 0)
        )
        
        return result
        
    except Exception as e:
        logger.error("Scheduled reminders task failed", error=str(e), task_id=self.request.id)
        return {
            "success": False,
            "error": str(e),
            "reminders_sent": 0,
            "errors": 1
        }


@celery_app.task(
    bind=True,
    name="bulk_sms_async",
    max_retries=2,
    default_retry_delay=120,
    queue="notifications"
)
def bulk_sms_async(
    self,
    sms_batch: List[Dict],
    tenant_id: str = None
):
    """
    Send bulk SMS messages asynchronously
    
    Args:
        self: Celery task instance
        sms_batch: List of SMS messages to send
        tenant_id: Tenant ID for logging
        
    Returns:
        Dict with bulk send results
    """
    try:
        logger.info(
            "Starting bulk SMS send",
            task_id=self.request.id,
            batch_size=len(sms_batch),
            tenant_id=tenant_id
        )
        
        # Process bulk SMS
        result = asyncio.run(_process_bulk_sms(sms_batch, self.request.id))
        
        logger.info(
            "Bulk SMS completed",
            task_id=self.request.id,
            sent=result.get("sent", 0),
            failed=result.get("failed", 0)
        )
        
        return result
        
    except Exception as e:
        logger.error("Bulk SMS task failed", error=str(e), task_id=self.request.id)
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay)
        
        return {
            "success": False,
            "error": str(e),
            "sent": 0,
            "failed": len(sms_batch)
        }


# Internal async helper functions

async def _update_appointment_sms_status(appointment_id: str, message_sid: str):
    """Update appointment with SMS confirmation status"""
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import update
            from app.models.appointment import Appointment
            
            stmt = (
                update(Appointment)
                .where(Appointment.id == appointment_id)
                .values(
                    sms_sent=True,
                    sms_sent_at=datetime.now(timezone.utc),
                    twilio_message_sid=message_sid
                )
            )
            
            await db.execute(stmt)
            await db.commit()
            
            logger.info("Appointment SMS status updated", appointment_id=appointment_id)
            
        except Exception as e:
            logger.error("Failed to update appointment SMS status", error=str(e))


async def _update_appointment_reminder_status(appointment_id: str, hours_before: int):
    """Update appointment with reminder status"""
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import update
            from app.models.appointment import Appointment
            
            # Update appropriate reminder flag
            update_data = {}
            if hours_before >= 24:
                update_data["reminder_24h_sent"] = True
            elif hours_before <= 2:
                update_data["reminder_2h_sent"] = True
            
            if update_data:
                stmt = (
                    update(Appointment)
                    .where(Appointment.id == appointment_id)
                    .values(**update_data)
                )
                
                await db.execute(stmt)
                await db.commit()
                
                logger.info("Appointment reminder status updated", appointment_id=appointment_id)
                
        except Exception as e:
            logger.error("Failed to update appointment reminder status", error=str(e))


async def _process_scheduled_reminders(task_id: str) -> Dict:
    """Process scheduled appointment reminders"""
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select, and_
            from app.models.appointment import Appointment
            
            now = datetime.now(timezone.utc)
            
            # Find appointments needing 24-hour reminders
            tomorrow = now + timedelta(hours=24)
            reminders_24h = await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.scheduled_datetime.between(now + timedelta(hours=23), tomorrow + timedelta(hours=1)),
                        Appointment.reminder_24h_sent == False,
                        Appointment.status == "scheduled",
                        Appointment.sms_sent == True  # Only remind confirmed appointments
                    )
                )
            )
            
            # Find appointments needing 2-hour reminders
            in_2_hours = now + timedelta(hours=2)
            reminders_2h = await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.scheduled_datetime.between(in_2_hours - timedelta(minutes=30), in_2_hours + timedelta(minutes=30)),
                        Appointment.reminder_2h_sent == False,
                        Appointment.status == "scheduled"
                    )
                )
            )
            
            reminders_sent = 0
            errors = 0
            
            # Send 24-hour reminders
            for appointment in reminders_24h.scalars():
                try:
                    send_appointment_reminder_async.delay(
                        appointment_id=appointment.id,
                        tenant_id=appointment.tenant_id,
                        patient_phone=appointment.patient_phone,
                        patient_name=appointment.patient_name,
                        appointment_datetime_iso=appointment.scheduled_datetime.isoformat(),
                        hours_before=24
                    )
                    reminders_sent += 1
                except Exception as e:
                    logger.error("Failed to queue 24h reminder", error=str(e), appointment_id=appointment.id)
                    errors += 1
            
            # Send 2-hour reminders
            for appointment in reminders_2h.scalars():
                try:
                    send_appointment_reminder_async.delay(
                        appointment_id=appointment.id,
                        tenant_id=appointment.tenant_id,
                        patient_phone=appointment.patient_phone,
                        patient_name=appointment.patient_name,
                        appointment_datetime_iso=appointment.scheduled_datetime.isoformat(),
                        hours_before=2
                    )
                    reminders_sent += 1
                except Exception as e:
                    logger.error("Failed to queue 2h reminder", error=str(e), appointment_id=appointment.id)
                    errors += 1
            
            return {
                "success": True,
                "reminders_sent": reminders_sent,
                "errors": errors,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error("Failed to process scheduled reminders", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "reminders_sent": 0,
                "errors": 1
            }


async def _process_bulk_sms(sms_batch: List[Dict], task_id: str) -> Dict:
    """Process bulk SMS sending"""
    sms_service = SMSService()
    sent = 0
    failed = 0
    results = []
    
    for sms_data in sms_batch:
        try:
            result = await sms_service.send_custom_message(
                patient_phone=sms_data["phone"],
                message=sms_data["message"]
            )
            
            if result["success"]:
                sent += 1
            else:
                failed += 1
            
            results.append({
                "phone": sms_data["phone"][:3] + "***",
                "success": result["success"],
                "error": result.get("error")
            })
            
            # Small delay between messages to avoid rate limits
            await asyncio.sleep(0.1)
            
        except Exception as e:
            failed += 1
            results.append({
                "phone": sms_data["phone"][:3] + "***",
                "success": False,
                "error": str(e)
            })
    
    return {
        "success": failed == 0,
        "sent": sent,
        "failed": failed,
        "results": results,
        "task_id": task_id
    }