"""
Voice configuration model for tenant-specific AI settings
Allows customization of AI behavior per dental practice
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class VoiceConfig(Base):
    """
    Voice AI configuration per tenant
    
    Allows each dental practice to customize:
    - AI model settings (Groq/OpenAI)
    - Voice characteristics (ElevenLabs/OpenAI TTS)
    - Response style and personality
    - Language and accent preferences
    - Business-specific prompts
    """
    __tablename__ = "voice_configs"
    
    # Foreign key to tenant (one-to-one relationship)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), primary_key=True)
    
    # AI Model Configuration
    ai_model = Column(String(50), default="llama3-8b-8192")  # Groq model
    ai_temperature = Column(String(5), default="0.7")  # Creativity level
    ai_max_tokens = Column(Integer, default=150)  # Response length limit
    
    # Voice/TTS Configuration
    voice_provider = Column(String(20), default="elevenlabs")  # elevenlabs/openai
    voice_name = Column(String(50), default="Rachel")  # ElevenLabs voice
    voice_speed = Column(String(5), default="1.0")  # Speech rate
    voice_stability = Column(String(5), default="0.75")  # Voice consistency
    
    # Response Style
    response_style = Column(String(20), default="professional")  # professional/friendly/casual
    greeting_style = Column(String(20), default="formal")  # formal/warm/casual
    personality = Column(String(50), default="helpful dental assistant")
    
    # Language Settings
    primary_language = Column(String(10), default="en")
    secondary_languages = Column(Text, nullable=True)  # JSON array of supported languages
    auto_detect_language = Column(Boolean, default=True)
    
    # Business Context
    practice_name = Column(String(255), nullable=True)
    practice_type = Column(String(50), default="dental")  # dental/orthodontics/oral_surgery
    office_hours = Column(Text, nullable=True)  # JSON object with hours
    booking_policy = Column(Text, nullable=True)  # Custom booking rules
    
    # Custom Prompts
    system_prompt = Column(Text, nullable=True)  # Override default system prompt
    greeting_message = Column(Text, nullable=True)  # Custom greeting
    closing_message = Column(Text, nullable=True)  # Custom goodbye
    
    # Call Behavior
    max_call_duration = Column(Integer, default=300)  # 5 minutes max
    enable_interruptions = Column(Boolean, default=True)  # Allow user interruptions
    confidence_threshold = Column(String(5), default="0.7")  # Min confidence for responses
    fallback_to_human = Column(Boolean, default=True)  # Transfer on low confidence
    
    # Integration Settings
    google_calendar_enabled = Column(Boolean, default=True)
    sms_confirmations = Column(Boolean, default=True)
    email_confirmations = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="voice_config")
    
    def __repr__(self):
        return f"<VoiceConfig(tenant_id='{self.tenant_id}', ai_model='{self.ai_model}', voice_name='{self.voice_name}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "tenant_id": self.tenant_id,
            "ai_model": self.ai_model,
            "ai_temperature": float(self.ai_temperature),
            "ai_max_tokens": self.ai_max_tokens,
            "voice_provider": self.voice_provider,
            "voice_name": self.voice_name,
            "voice_speed": float(self.voice_speed),
            "voice_stability": float(self.voice_stability),
            "response_style": self.response_style,
            "greeting_style": self.greeting_style,
            "personality": self.personality,
            "primary_language": self.primary_language,
            "secondary_languages": self.secondary_languages,
            "auto_detect_language": self.auto_detect_language,
            "practice_name": self.practice_name,
            "practice_type": self.practice_type,
            "office_hours": self.office_hours,
            "booking_policy": self.booking_policy,
            "system_prompt": self.system_prompt,
            "greeting_message": self.greeting_message,
            "closing_message": self.closing_message,
            "max_call_duration": self.max_call_duration,
            "enable_interruptions": self.enable_interruptions,
            "confidence_threshold": float(self.confidence_threshold),
            "fallback_to_human": self.fallback_to_human,
            "google_calendar_enabled": self.google_calendar_enabled,
            "sms_confirmations": self.sms_confirmations,
            "email_confirmations": self.email_confirmations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for AI, with fallback to default"""
        if self.system_prompt:
            return self.system_prompt
        
        # Default system prompt
        practice_name = self.practice_name or "our dental practice"
        return f"""You are a helpful AI assistant for {practice_name}. 
        
Your role is to:
1. Schedule dental appointments in a {self.response_style} manner
2. Answer questions about office hours and services
3. Collect patient information (name, phone, preferred time)
4. Confirm appointments via the booking system
5. Transfer complex medical questions to human staff

Style: {self.greeting_style} greeting, {self.response_style} responses
Keep responses under {self.ai_max_tokens} tokens and maintain a {self.personality} personality.

If confidence is below {self.confidence_threshold}, offer to transfer to a human representative."""
    
    def get_greeting_message(self) -> str:
        """Get personalized greeting message"""
        if self.greeting_message:
            return self.greeting_message
        
        practice_name = self.practice_name or "our dental practice"
        
        if self.greeting_style == "formal":
            return f"Thank you for calling {practice_name}. How may I assist you today?"
        elif self.greeting_style == "warm":
            return f"Hello! Welcome to {practice_name}. I'm here to help with your appointment needs."
        else:  # casual
            return f"Hi there! You've reached {practice_name}. What can I do for you?"