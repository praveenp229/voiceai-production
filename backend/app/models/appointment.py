"""
Appointment model for scheduled dental visits
Integrates with Google Calendar and supports SMS confirmations
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Appointment(Base):
    """
    Appointment model for dental visit scheduling
    
    Features:
    - Google Calendar integration
    - SMS/email confirmations
    - Status tracking and updates
    - Patient history linking
    - Timezone handling
    """
    __tablename__ = "appointments"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relationships
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    call_log_id = Column(String(36), ForeignKey("call_logs.id"), nullable=True, index=True)
    
    # Patient information (encrypted)
    patient_name = Column(String(255), nullable=False)
    patient_phone = Column(String(20), nullable=False, index=True)
    patient_email = Column(String(255), nullable=True)
    
    # Appointment details
    appointment_type = Column(String(100), default="General Consultation")
    appointment_reason = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Scheduling
    scheduled_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(String(10), default="30")
    timezone = Column(String(50), default="America/Chicago")
    
    # Status tracking
    status = Column(String(20), default="scheduled", index=True)  # scheduled/confirmed/cancelled/completed/no_show
    confirmation_status = Column(String(20), default="pending")  # pending/confirmed/declined
    
    # Integration IDs
    google_event_id = Column(String(255), nullable=True, unique=True)  # Google Calendar event ID
    twilio_message_sid = Column(String(64), nullable=True)  # SMS confirmation ID
    
    # Confirmations
    sms_sent = Column(Boolean, default=False)
    sms_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Reminder tracking
    reminder_24h_sent = Column(Boolean, default=False)
    reminder_2h_sent = Column(Boolean, default=False)
    
    # Cancellation/Rescheduling
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    rescheduled_from = Column(String(36), nullable=True)  # Original appointment ID if rescheduled
    
    # Notes and history
    notes = Column(Text, nullable=True)  # Staff notes
    ai_conversation_summary = Column(Text, nullable=True)  # Summary of AI conversation that led to booking
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="appointments")
    customer = relationship("Customer", back_populates="appointments")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_appointment_tenant_date", "tenant_id", "scheduled_datetime"),
        Index("idx_appointment_customer_date", "customer_id", "scheduled_datetime"),
        Index("idx_appointment_phone_date", "patient_phone", "scheduled_datetime"),
        Index("idx_appointment_status_date", "status", "scheduled_datetime"),
        Index("idx_appointment_confirmation", "confirmation_status", "scheduled_datetime"),
        Index("idx_appointment_google_event", "google_event_id"),
    )
    
    def __repr__(self):
        return f"<Appointment(id='{self.id}', patient='{self.patient_name}', date='{self.scheduled_datetime}', status='{self.status}')>"
    
    def to_dict(self, include_pii: bool = False):
        """
        Convert to dictionary for API responses
        
        Args:
            include_pii: Whether to include personally identifiable information
        """
        base_data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "customer_id": self.customer_id,
            "call_log_id": self.call_log_id,
            "appointment_type": self.appointment_type,
            "appointment_reason": self.appointment_reason,
            "special_instructions": self.special_instructions,
            "scheduled_datetime": self.scheduled_datetime.isoformat() if self.scheduled_datetime else None,
            "duration_minutes": int(self.duration_minutes),
            "timezone": self.timezone,
            "status": self.status,
            "confirmation_status": self.confirmation_status,
            "google_event_id": self.google_event_id,
            "sms_sent": self.sms_sent,
            "sms_sent_at": self.sms_sent_at.isoformat() if self.sms_sent_at else None,
            "email_sent": self.email_sent,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None,
            "reminder_24h_sent": self.reminder_24h_sent,
            "reminder_2h_sent": self.reminder_2h_sent,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancellation_reason": self.cancellation_reason,
            "rescheduled_from": self.rescheduled_from,
            "notes": self.notes,
            "ai_conversation_summary": self.ai_conversation_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_pii:
            base_data.update({
                "patient_name": self.patient_name,
                "patient_phone": self.patient_phone,
                "patient_email": self.patient_email,
            })
        else:
            # Masked PII for non-authorized access
            base_data.update({
                "patient_name": self.patient_name[:2] + "***" if self.patient_name else None,
                "patient_phone": self.mask_phone(),
                "patient_email": "***@***.com" if self.patient_email else None,
            })
        
        return base_data
    
    def mask_phone(self) -> str:
        """Return masked phone number for logging"""
        if not self.patient_phone:
            return "Unknown"
        return f"{self.patient_phone[:3]}***{self.patient_phone[-2:]}" if len(self.patient_phone) > 5 else "***"
    
    def is_upcoming(self) -> bool:
        """Check if appointment is in the future"""
        from datetime import datetime, timezone
        return self.scheduled_datetime > datetime.now(timezone.utc)
    
    def is_today(self) -> bool:
        """Check if appointment is today"""
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        return self.scheduled_datetime.date() == today
    
    def get_confirmation_message(self) -> str:
        """Generate SMS confirmation message"""
        formatted_date = self.scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")
        return f"Appointment confirmed for {formatted_date}. Reply 'C' to cancel. Thank you!"
    
    def get_reminder_message(self, hours_before: int) -> str:
        """Generate reminder message"""
        formatted_date = self.scheduled_datetime.strftime("%B %d at %I:%M %p")
        return f"Reminder: You have a dental appointment on {formatted_date} ({hours_before}h from now). Reply 'C' to cancel."
    
    def cancel(self, reason: str = None):
        """Cancel the appointment"""
        from datetime import datetime, timezone
        self.status = "cancelled"
        self.cancelled_at = datetime.now(timezone.utc)
        self.cancellation_reason = reason
    
    def confirm(self):
        """Confirm the appointment"""
        self.confirmation_status = "confirmed"
        if self.status == "scheduled":
            self.status = "confirmed"
    
    def complete(self):
        """Mark appointment as completed"""
        self.status = "completed"
    
    def mark_no_show(self):
        """Mark appointment as no-show"""
        self.status = "no_show"