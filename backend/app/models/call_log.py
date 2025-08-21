"""
Call log model for tracking all voice interactions
Includes conversation history, performance metrics, and audit trails
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class CallLog(Base):
    """
    Call log for voice AI interactions
    
    Tracks:
    - Complete conversation flow
    - Performance metrics (latency, confidence)
    - Appointment outcomes
    - Error handling and fallbacks
    - HIPAA audit trail
    """
    __tablename__ = "call_logs"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relationships
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True, index=True)
    
    # Call identification
    call_sid = Column(String(64), nullable=False, unique=True, index=True)  # Twilio call ID
    caller_phone = Column(String(20), nullable=False, index=True)
    
    # Call metadata
    call_direction = Column(String(10), default="inbound")  # inbound/outbound
    call_status = Column(String(20), nullable=True)  # completed/failed/busy/no-answer
    call_duration = Column(Integer, nullable=True)  # Total duration in seconds
    
    # Conversation content (encrypted in production)
    conversation = Column(Text, nullable=True)  # Full conversation JSON
    user_input = Column(Text, nullable=True)  # Last user message
    ai_response = Column(Text, nullable=True)  # Last AI response
    language_detected = Column(String(10), default="en")
    
    # AI Performance metrics
    total_turns = Column(Integer, default=0)  # Number of back-and-forth exchanges
    avg_response_time = Column(Float, nullable=True)  # Average AI response time
    avg_confidence = Column(Float, nullable=True)  # Average AI confidence score
    errors_count = Column(Integer, default=0)  # Number of errors during call
    
    # Outcomes
    appointment_scheduled = Column(Boolean, default=False)
    appointment_id = Column(String(36), nullable=True)  # Link to appointment if created
    transferred_to_human = Column(Boolean, default=False)
    call_successful = Column(Boolean, default=True)
    
    # Technical details
    audio_url = Column(String(500), nullable=True)  # S3 URL for audio recording
    transcription_accuracy = Column(Float, nullable=True)  # STT accuracy score
    ai_model_used = Column(String(50), nullable=True)  # Which AI model was used
    voice_used = Column(String(50), nullable=True)  # Which TTS voice was used
    
    # Cost tracking
    stt_cost = Column(Float, default=0.0)  # Speech-to-text cost
    llm_cost = Column(Float, default=0.0)  # LLM inference cost
    tts_cost = Column(Float, default=0.0)  # Text-to-speech cost
    total_cost = Column(Float, default=0.0)  # Total AI cost for this call
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_type = Column(String(50), nullable=True)  # stt_error/llm_error/tts_error/system_error
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="call_logs")
    customer = relationship("Customer", back_populates="call_logs")
    
    # Indexes for performance and analytics
    __table_args__ = (
        Index("idx_call_tenant_created", "tenant_id", "created_at"),
        Index("idx_call_customer_created", "customer_id", "created_at"),
        Index("idx_call_phone_created", "caller_phone", "created_at"),
        Index("idx_call_status_created", "call_status", "created_at"),
        Index("idx_call_successful_created", "call_successful", "created_at"),
        Index("idx_call_appointment_scheduled", "appointment_scheduled", "created_at"),
    )
    
    def __repr__(self):
        return f"<CallLog(id='{self.id}', call_sid='{self.call_sid}', phone='{self.caller_phone[:3]}***')>"
    
    def to_dict(self, include_conversation: bool = False, include_pii: bool = False):
        """
        Convert to dictionary for API responses
        
        Args:
            include_conversation: Whether to include full conversation data
            include_pii: Whether to include personally identifiable information
        """
        base_data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "customer_id": self.customer_id,
            "call_sid": self.call_sid,
            "call_direction": self.call_direction,
            "call_status": self.call_status,
            "call_duration": self.call_duration,
            "language_detected": self.language_detected,
            "total_turns": self.total_turns,
            "avg_response_time": self.avg_response_time,
            "avg_confidence": self.avg_confidence,
            "errors_count": self.errors_count,
            "appointment_scheduled": self.appointment_scheduled,
            "appointment_id": self.appointment_id,
            "transferred_to_human": self.transferred_to_human,
            "call_successful": self.call_successful,
            "transcription_accuracy": self.transcription_accuracy,
            "ai_model_used": self.ai_model_used,
            "voice_used": self.voice_used,
            "total_cost": self.total_cost,
            "error_type": self.error_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_pii:
            base_data["caller_phone"] = self.caller_phone
        else:
            base_data["caller_phone"] = self.mask_phone()
        
        if include_conversation:
            if include_pii:
                base_data.update({
                    "conversation": self.conversation,
                    "user_input": self.user_input,
                    "ai_response": self.ai_response,
                    "audio_url": self.audio_url,
                    "error_message": self.error_message,
                })
            else:
                # Mask PII in conversation data
                base_data.update({
                    "user_input": "[REDACTED]" if self.user_input else None,
                    "ai_response": self.ai_response,  # AI responses generally don't contain PII
                })
        
        return base_data
    
    def mask_phone(self) -> str:
        """Return masked phone number for logging"""
        if not self.caller_phone:
            return "Unknown"
        return f"{self.caller_phone[:3]}***{self.caller_phone[-2:]}" if len(self.caller_phone) > 5 else "***"
    
    def add_turn(self, user_input: str, ai_response: str, response_time: float, confidence: float):
        """Add a conversation turn and update metrics"""
        self.total_turns += 1
        self.user_input = user_input
        self.ai_response = ai_response
        
        # Update running averages
        if self.avg_response_time is None:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time * (self.total_turns - 1) + response_time) / self.total_turns
        
        if self.avg_confidence is None:
            self.avg_confidence = confidence
        else:
            self.avg_confidence = (self.avg_confidence * (self.total_turns - 1) + confidence) / self.total_turns
    
    def mark_error(self, error_type: str, error_message: str):
        """Record an error during the call"""
        self.errors_count += 1
        self.error_type = error_type
        self.error_message = error_message
        self.call_successful = False
    
    def calculate_total_cost(self):
        """Calculate and update total cost"""
        self.total_cost = self.stt_cost + self.llm_cost + self.tts_cost