"""
Google Calendar service for appointment scheduling
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class CalendarService:
    """
    Google Calendar integration service
    
    Features:
    - Check available appointment slots
    - Schedule appointments
    - Cancel/reschedule appointments
    - Sync with tenant calendars
    """
    
    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID or "primary"
    
    async def get_available_slots(
        self,
        tenant_id: str,
        date_start: datetime = None,
        date_end: datetime = None,
        days_ahead: int = 7,
        slot_duration: int = 30
    ) -> List[str]:
        """
        Get available appointment slots
        
        Args:
            tenant_id: Tenant ID for calendar lookup
            date_start: Start date for availability search
            date_end: End date for availability search  
            days_ahead: Number of days to look ahead
            slot_duration: Duration of each slot in minutes
            
        Returns:
            List of available time slots as strings
        """
        try:
            logger.info("Getting available slots", tenant_id=tenant_id, days_ahead=days_ahead)
            
            # For now, return mock available slots
            # In production, this would integrate with Google Calendar API
            
            if not date_start:
                date_start = datetime.now(timezone.utc)
            
            if not date_end:
                date_end = date_start + timedelta(days=days_ahead)
            
            # Mock business hours: 9 AM to 5 PM, Monday to Friday
            available_slots = []
            current_date = date_start.replace(hour=9, minute=0, second=0, microsecond=0)
            
            while current_date < date_end:
                # Skip weekends
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    # Generate slots from 9 AM to 5 PM
                    slot_time = current_date.replace(hour=9, minute=0)
                    while slot_time.hour < 17:
                        # Format slot time
                        slot_str = slot_time.strftime("%A, %B %d at %I:%M %p")
                        available_slots.append(slot_str)
                        
                        # Move to next slot
                        slot_time += timedelta(minutes=slot_duration)
                        
                        # Stop at 5 PM
                        if slot_time.hour >= 17:
                            break
                
                # Move to next day
                current_date += timedelta(days=1)
            
            # Return first 10 slots
            available_slots = available_slots[:10]
            
            logger.info("Available slots retrieved", tenant_id=tenant_id, count=len(available_slots))
            return available_slots
            
        except Exception as e:
            logger.error("Failed to get available slots", error=str(e), tenant_id=tenant_id)
            return []
    
    async def schedule_appointment(
        self,
        tenant_id: str,
        appointment_datetime: datetime,
        duration_minutes: int = 30,
        patient_name: str = "Unknown Patient",
        patient_phone: str = None,
        appointment_type: str = "Dental Appointment",
        notes: str = None
    ) -> Dict:
        """
        Schedule an appointment in Google Calendar
        
        Args:
            tenant_id: Tenant ID
            appointment_datetime: Appointment date and time
            duration_minutes: Appointment duration
            patient_name: Patient name
            patient_phone: Patient phone number
            appointment_type: Type of appointment
            notes: Additional notes
            
        Returns:
            Dict with success status and event details
        """
        try:
            logger.info(
                "Scheduling appointment",
                tenant_id=tenant_id,
                patient_name=patient_name,
                datetime=appointment_datetime.isoformat()
            )
            
            # Mock Google Calendar event creation
            # In production, this would use Google Calendar API
            
            event_id = f"mock_event_{tenant_id}_{int(appointment_datetime.timestamp())}"
            
            # Mock successful scheduling
            result = {
                "success": True,
                "event_id": event_id,
                "summary": f"{appointment_type} - {patient_name}",
                "start_time": appointment_datetime.isoformat(),
                "end_time": (appointment_datetime + timedelta(minutes=duration_minutes)).isoformat(),
                "patient_phone": patient_phone,
                "notes": notes,
                "calendar_link": f"https://calendar.google.com/calendar/event?eid={event_id}"
            }
            
            logger.info("Appointment scheduled successfully", tenant_id=tenant_id, event_id=event_id)
            return result
            
        except Exception as e:
            logger.error("Failed to schedule appointment", error=str(e), tenant_id=tenant_id)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cancel_appointment(
        self,
        tenant_id: str,
        event_id: str,
        reason: str = None
    ) -> Dict:
        """
        Cancel an appointment in Google Calendar
        
        Args:
            tenant_id: Tenant ID
            event_id: Google Calendar event ID
            reason: Cancellation reason
            
        Returns:
            Dict with success status
        """
        try:
            logger.info("Canceling appointment", tenant_id=tenant_id, event_id=event_id, reason=reason)
            
            # Mock cancellation
            # In production, this would delete/update the Google Calendar event
            
            logger.info("Appointment canceled successfully", tenant_id=tenant_id, event_id=event_id)
            return {
                "success": True,
                "event_id": event_id,
                "reason": reason
            }
            
        except Exception as e:
            logger.error("Failed to cancel appointment", error=str(e), tenant_id=tenant_id, event_id=event_id)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def reschedule_appointment(
        self,
        tenant_id: str,
        event_id: str,
        new_datetime: datetime,
        reason: str = None
    ) -> Dict:
        """
        Reschedule an appointment in Google Calendar
        
        Args:
            tenant_id: Tenant ID
            event_id: Google Calendar event ID
            new_datetime: New appointment datetime
            reason: Reschedule reason
            
        Returns:
            Dict with success status and updated event details
        """
        try:
            logger.info(
                "Rescheduling appointment",
                tenant_id=tenant_id,
                event_id=event_id,
                new_datetime=new_datetime.isoformat()
            )
            
            # Mock rescheduling
            # In production, this would update the Google Calendar event
            
            result = {
                "success": True,
                "event_id": event_id,
                "old_datetime": "previous_time",  # Would be retrieved from calendar
                "new_datetime": new_datetime.isoformat(),
                "reason": reason
            }
            
            logger.info("Appointment rescheduled successfully", tenant_id=tenant_id, event_id=event_id)
            return result
            
        except Exception as e:
            logger.error("Failed to reschedule appointment", error=str(e), tenant_id=tenant_id, event_id=event_id)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_appointment_details(
        self,
        tenant_id: str,
        event_id: str
    ) -> Optional[Dict]:
        """
        Get appointment details from Google Calendar
        
        Args:
            tenant_id: Tenant ID
            event_id: Google Calendar event ID
            
        Returns:
            Dict with appointment details or None if not found
        """
        try:
            logger.info("Getting appointment details", tenant_id=tenant_id, event_id=event_id)
            
            # Mock appointment details
            # In production, this would retrieve from Google Calendar API
            
            appointment_details = {
                "event_id": event_id,
                "summary": "Dental Appointment - John Doe",
                "start_time": "2024-01-25T10:00:00Z",
                "end_time": "2024-01-25T10:30:00Z",
                "patient_name": "John Doe",
                "patient_phone": "+1234567890",
                "status": "confirmed",
                "location": "Dental Office",
                "notes": "Regular checkup"
            }
            
            logger.info("Appointment details retrieved", tenant_id=tenant_id, event_id=event_id)
            return appointment_details
            
        except Exception as e:
            logger.error("Failed to get appointment details", error=str(e), tenant_id=tenant_id, event_id=event_id)
            return None
    
    async def check_slot_availability(
        self,
        tenant_id: str,
        appointment_datetime: datetime,
        duration_minutes: int = 30
    ) -> bool:
        """
        Check if a specific time slot is available
        
        Args:
            tenant_id: Tenant ID
            appointment_datetime: Requested appointment time
            duration_minutes: Appointment duration
            
        Returns:
            True if slot is available, False otherwise
        """
        try:
            logger.info(
                "Checking slot availability",
                tenant_id=tenant_id,
                datetime=appointment_datetime.isoformat()
            )
            
            # Mock availability check
            # In production, this would query Google Calendar for conflicts
            
            # Simple mock: available if it's during business hours and in the future
            now = datetime.now(timezone.utc)
            if appointment_datetime <= now:
                return False
            
            # Check if it's during business hours (9 AM to 5 PM, Monday-Friday)
            if appointment_datetime.weekday() >= 5:  # Weekend
                return False
            
            if appointment_datetime.hour < 9 or appointment_datetime.hour >= 17:
                return False
            
            # Mock: assume 80% of slots are available
            import random
            is_available = random.random() < 0.8
            
            logger.info(
                "Slot availability checked",
                tenant_id=tenant_id,
                available=is_available
            )
            return is_available
            
        except Exception as e:
            logger.error("Failed to check slot availability", error=str(e), tenant_id=tenant_id)
            return False