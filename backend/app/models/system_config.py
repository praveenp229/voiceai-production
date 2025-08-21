"""
System configuration model for global application settings
Stores key-value pairs for system-wide configuration
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Index
from sqlalchemy.sql import func
from app.core.database import Base


class SystemConfig(Base):
    """
    System configuration key-value store
    
    Used for:
    - Global application settings
    - Feature flags
    - API keys and secrets (encrypted)
    - Operational parameters
    - Default values for new tenants
    """
    __tablename__ = "system_config"
    
    # Configuration key (primary key)
    key = Column(String(100), primary_key=True)
    
    # Configuration value (can be JSON)
    value = Column(Text, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    category = Column(String(50), default="general", index=True)
    is_encrypted = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)  # Can be exposed via API
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_config_category", "category"),
        Index("idx_config_public", "is_public"),
    )
    
    def __repr__(self):
        return f"<SystemConfig(key='{self.key}', category='{self.category}')>"
    
    def to_dict(self, include_value: bool = True):
        """Convert to dictionary for API responses"""
        data = {
            "key": self.key,
            "description": self.description,
            "category": self.category,
            "is_encrypted": self.is_encrypted,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_value:
            if self.is_encrypted:
                data["value"] = "[ENCRYPTED]"
            else:
                data["value"] = self.value
        
        return data


# Common configuration keys and their defaults
DEFAULT_CONFIGS = {
    # AI Service Settings
    "DEFAULT_AI_MODEL": {
        "value": "llama3-8b-8192",
        "description": "Default AI model for new tenants",
        "category": "ai",
        "is_public": True
    },
    "DEFAULT_VOICE_PROVIDER": {
        "value": "elevenlabs",
        "description": "Default TTS provider for new tenants",
        "category": "ai",
        "is_public": True
    },
    "AI_FALLBACK_ENABLED": {
        "value": "true",
        "description": "Enable fallback to OpenAI when primary AI services fail",
        "category": "ai",
        "is_public": False
    },
    
    # Performance Settings
    "MAX_CONCURRENT_CALLS": {
        "value": "100",
        "description": "Maximum number of concurrent voice calls",
        "category": "performance",
        "is_public": False
    },
    "RESPONSE_TIMEOUT_SECONDS": {
        "value": "30",
        "description": "Maximum time to wait for AI response",
        "category": "performance",
        "is_public": False
    },
    "CALL_DURATION_LIMIT": {
        "value": "300",
        "description": "Maximum call duration in seconds",
        "category": "performance",
        "is_public": True
    },
    
    # Security Settings
    "ENCRYPTION_ENABLED": {
        "value": "true",
        "description": "Enable PII encryption in database",
        "category": "security",
        "is_public": False
    },
    "AUDIT_LOGGING": {
        "value": "true",
        "description": "Enable comprehensive audit logging",
        "category": "security",
        "is_public": False
    },
    "JWT_EXPIRATION_HOURS": {
        "value": "24",
        "description": "JWT token expiration time in hours",
        "category": "security",
        "is_public": False
    },
    
    # Default Voice Configuration
    "DEFAULT_VOICE_SPEED": {
        "value": "1.0",
        "description": "Default TTS speech rate",
        "category": "voice",
        "is_public": True
    },
    "DEFAULT_VOICE_STABILITY": {
        "value": "0.75",
        "description": "Default TTS voice stability",
        "category": "voice",
        "is_public": True
    },
    "DEFAULT_CONFIDENCE_THRESHOLD": {
        "value": "0.7",
        "description": "Default minimum confidence for AI responses",
        "category": "voice",
        "is_public": True
    },
    
    # Business Settings
    "DEFAULT_APPOINTMENT_DURATION": {
        "value": "30",
        "description": "Default appointment duration in minutes",
        "category": "business",
        "is_public": True
    },
    "SMS_CONFIRMATIONS_ENABLED": {
        "value": "true",
        "description": "Enable SMS appointment confirmations by default",
        "category": "business",
        "is_public": True
    },
    "GOOGLE_CALENDAR_ENABLED": {
        "value": "true",
        "description": "Enable Google Calendar integration by default",
        "category": "business",
        "is_public": True
    },
    
    # Cost Management
    "COST_TRACKING_ENABLED": {
        "value": "true",
        "description": "Track AI service costs per call",
        "category": "cost",
        "is_public": False
    },
    "MONTHLY_COST_LIMIT": {
        "value": "1000",
        "description": "Monthly cost limit in USD",
        "category": "cost",
        "is_public": False
    },
    
    # Feature Flags
    "MULTILANGUAGE_ENABLED": {
        "value": "true",
        "description": "Enable multi-language support",
        "category": "features",
        "is_public": True
    },
    "REAL_TIME_STREAMING": {
        "value": "true",
        "description": "Enable real-time audio streaming",
        "category": "features",
        "is_public": False
    },
    "HUMAN_FALLBACK_ENABLED": {
        "value": "true",
        "description": "Enable fallback to human operators",
        "category": "features",
        "is_public": True
    },
    
    # Monitoring
    "METRICS_ENABLED": {
        "value": "true",
        "description": "Enable Prometheus metrics collection",
        "category": "monitoring",
        "is_public": False
    },
    "SENTRY_ENABLED": {
        "value": "true",
        "description": "Enable Sentry error tracking",
        "category": "monitoring",
        "is_public": False
    },
}