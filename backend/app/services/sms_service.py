"""
SMS service for appointment confirmations and notifications
"""

from typing import Dict, Optional
from datetime import datetime
import structlog

from app.core.config import settings
from app.utils.twilio_utils import send_twilio_sms, format_phone_for_display

logger = structlog.get_logger(__name__)


class SMSService:
    """
    SMS service for patient notifications
    
    Features:
    - Appointment confirmations
    - Appointment reminders
    - Cancellation notifications
    - Custom message templates
    """
    
    def __init__(self):
        self.from_phone = settings.TWILIO_PHONE_NUMBER
    
    async def send_appointment_confirmation(
        self,
        patient_phone: str,
        patient_name: str,
        appointment_datetime: datetime,
        practice_name: str = "our dental practice",
        appointment_type: str = "appointment"
    ) -> Dict:
        """
        Send appointment confirmation SMS
        
        Args:
            patient_phone: Patient's phone number
            patient_name: Patient's name
            appointment_datetime: Appointment date and time
            practice_name: Name of dental practice
            appointment_type: Type of appointment
            
        Returns:
            Dict with success status and message details
        """
        try:
            logger.info(
                "Sending appointment confirmation",
                patient_phone=f"{patient_phone[:3]}***",
                appointment_date=appointment_datetime.strftime("%Y-%m-%d %H:%M")
            )
            
            # Format appointment date/time
            formatted_date = appointment_datetime.strftime("%A, %B %d")
            formatted_time = appointment_datetime.strftime("%I:%M %p")
            
            # Create confirmation message
            message = f"""Hello {patient_name}! Your {appointment_type} at {practice_name} is confirmed for {formatted_date} at {formatted_time}.

Reply 'C' to cancel or call us if you need to reschedule. See you then!"""
            
            # Send SMS
            result = await send_twilio_sms(
                to_phone=patient_phone,
                message=message,
                from_phone=self.from_phone
            )
            
            if result["success"]:
                logger.info("Appointment confirmation sent", patient_phone=f"{patient_phone[:3]}***")
                return {
                    "success": True,
                    "message_type": "confirmation",
                    "message_sid": result["message_sid"],
                    "message": message
                }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error("Failed to send appointment confirmation", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_appointment_reminder(
        self,
        patient_phone: str,
        patient_name: str,
        appointment_datetime: datetime,
        practice_name: str = "our dental practice",
        hours_before: int = 24
    ) -> Dict:
        """
        Send appointment reminder SMS
        
        Args:
            patient_phone: Patient's phone number
            patient_name: Patient's name
            appointment_datetime: Appointment date and time
            practice_name: Name of dental practice
            hours_before: Hours before appointment (for message content)
            
        Returns:
            Dict with success status and message details
        """
        try:
            logger.info(
                "Sending appointment reminder",
                patient_phone=f"{patient_phone[:3]}***",
                hours_before=hours_before
            )
            
            # Format appointment date/time
            formatted_date = appointment_datetime.strftime("%A, %B %d")
            formatted_time = appointment_datetime.strftime("%I:%M %p")
            
            # Create reminder message based on timing
            if hours_before >= 24:
                timing_text = "tomorrow"
            elif hours_before >= 2:
                timing_text = f"in {hours_before} hours"
            else:
                timing_text = "soon"
            
            message = f"""Hi {patient_name}, this is a reminder that you have an appointment at {practice_name} {timing_text} on {formatted_date} at {formatted_time}.

Reply 'C' to cancel or call us if needed. Thanks!"""
            
            # Send SMS
            result = await send_twilio_sms(
                to_phone=patient_phone,
                message=message,
                from_phone=self.from_phone
            )
            
            if result["success"]:
                logger.info("Appointment reminder sent", patient_phone=f"{patient_phone[:3]}***")
                return {
                    "success": True,
                    "message_type": "reminder",
                    "message_sid": result["message_sid"],
                    "hours_before": hours_before,
                    "message": message
                }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error("Failed to send appointment reminder", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_cancellation_notification(
        self,
        patient_phone: str,
        patient_name: str,
        appointment_datetime: datetime,
        practice_name: str = "our dental practice",
        reason: str = None
    ) -> Dict:
        """
        Send appointment cancellation notification SMS
        
        Args:
            patient_phone: Patient's phone number
            patient_name: Patient's name
            appointment_datetime: Original appointment date and time
            practice_name: Name of dental practice
            reason: Cancellation reason (optional)
            
        Returns:
            Dict with success status and message details
        """
        try:
            logger.info(
                "Sending cancellation notification",
                patient_phone=f"{patient_phone[:3]}***"
            )
            
            # Format appointment date/time
            formatted_date = appointment_datetime.strftime("%A, %B %d")
            formatted_time = appointment_datetime.strftime("%I:%M %p")
            
            # Create cancellation message
            message = f"""Hi {patient_name}, your appointment at {practice_name} on {formatted_date} at {formatted_time} has been canceled."""
            
            if reason:
                message += f" Reason: {reason}."
            
            message += f"\n\nPlease call us to reschedule. Thank you!"
            
            # Send SMS
            result = await send_twilio_sms(
                to_phone=patient_phone,
                message=message,
                from_phone=self.from_phone
            )
            
            if result["success"]:
                logger.info("Cancellation notification sent", patient_phone=f"{patient_phone[:3]}***")
                return {
                    "success": True,
                    "message_type": "cancellation",
                    "message_sid": result["message_sid"],
                    "message": message
                }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error("Failed to send cancellation notification", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_reschedule_notification(
        self,
        patient_phone: str,
        patient_name: str,
        old_appointment_datetime: datetime,
        new_appointment_datetime: datetime,
        practice_name: str = "our dental practice"
    ) -> Dict:
        """
        Send appointment reschedule notification SMS
        
        Args:
            patient_phone: Patient's phone number
            patient_name: Patient's name
            old_appointment_datetime: Original appointment date and time
            new_appointment_datetime: New appointment date and time
            practice_name: Name of dental practice
            
        Returns:
            Dict with success status and message details
        """
        try:
            logger.info(
                "Sending reschedule notification",
                patient_phone=f"{patient_phone[:3]}***"
            )
            
            # Format dates/times
            old_formatted = old_appointment_datetime.strftime("%A, %B %d at %I:%M %p")
            new_formatted_date = new_appointment_datetime.strftime("%A, %B %d")
            new_formatted_time = new_appointment_datetime.strftime("%I:%M %p")
            
            # Create reschedule message
            message = f"""Hi {patient_name}, your appointment at {practice_name} has been rescheduled.

Original: {old_formatted}
New: {new_formatted_date} at {new_formatted_time}

Reply 'C' to cancel or call us if this doesn't work. Thanks!"""
            
            # Send SMS
            result = await send_twilio_sms(
                to_phone=patient_phone,
                message=message,
                from_phone=self.from_phone
            )
            
            if result["success"]:
                logger.info("Reschedule notification sent", patient_phone=f"{patient_phone[:3]}***")
                return {
                    "success": True,
                    "message_type": "reschedule",
                    "message_sid": result["message_sid"],
                    "message": message
                }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error("Failed to send reschedule notification", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_custom_message(
        self,
        patient_phone: str,
        message: str
    ) -> Dict:
        """
        Send custom SMS message
        
        Args:
            patient_phone: Patient's phone number
            message: Custom message to send
            
        Returns:
            Dict with success status and message details
        """
        try:
            logger.info(
                "Sending custom SMS message",
                patient_phone=f"{patient_phone[:3]}***",
                message_length=len(message)
            )
            
            # Send SMS
            result = await send_twilio_sms(
                to_phone=patient_phone,
                message=message,
                from_phone=self.from_phone
            )
            
            if result["success"]:
                logger.info("Custom SMS sent", patient_phone=f"{patient_phone[:3]}***")
                return {
                    "success": True,
                    "message_type": "custom",
                    "message_sid": result["message_sid"],
                    "message": message
                }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error("Failed to send custom SMS", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_incoming_sms(
        self,
        from_phone: str,
        message_body: str,
        tenant_id: str = None
    ) -> Dict:
        """
        Handle incoming SMS messages (for cancellations, etc.)
        
        Args:
            from_phone: Sender's phone number
            message_body: SMS message content
            tenant_id: Tenant ID (optional)
            
        Returns:
            Dict with response message and action to take
        """
        try:
            logger.info(
                "Handling incoming SMS",
                from_phone=f"{from_phone[:3]}***",
                message_body=message_body[:50] + "..." if len(message_body) > 50 else message_body
            )
            
            message_lower = message_body.lower().strip()
            
            # Handle cancellation requests
            if message_lower in ['c', 'cancel', 'cancel appointment']:
                return {
                    "action": "cancel_appointment",
                    "response_message": "We've received your cancellation request. We'll process this shortly and send you a confirmation. Thank you!",
                    "success": True
                }
            
            # Handle reschedule requests
            elif any(word in message_lower for word in ['reschedule', 'move', 'change', 'different time']):
                return {
                    "action": "request_reschedule",
                    "response_message": "We've received your reschedule request. One of our team members will contact you shortly with available times. Thank you!",
                    "success": True
                }
            
            # Handle confirmation requests
            elif any(word in message_lower for word in ['confirm', 'yes', 'ok', 'confirmed']):
                return {
                    "action": "confirm_appointment",
                    "response_message": "Thank you for confirming your appointment! We look forward to seeing you.",
                    "success": True
                }
            
            # Handle general inquiries
            else:
                return {
                    "action": "general_inquiry",
                    "response_message": "Thank you for your message. Our team will respond during business hours. For urgent matters, please call our office directly.",
                    "success": True
                }
                
        except Exception as e:
            logger.error("Failed to handle incoming SMS", error=str(e))
            return {
                "action": "error",
                "response_message": "Sorry, we had trouble processing your message. Please call our office directly.",
                "success": False,
                "error": str(e)
            }