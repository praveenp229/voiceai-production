"""
Application configuration using Pydantic Settings
Handles all environment variables and configuration validation
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import os


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # ===========================================
    # BASIC SETTINGS
    # ===========================================
    APP_NAME: str = "VoiceAI 2.0"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # ===========================================
    # DATABASE
    # ===========================================
    DATABASE_URL: str = "sqlite:///./voiceai.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # ===========================================
    # AI SERVICES (Cost-Optimized)
    # ===========================================
    # Groq (90% cheaper than OpenAI)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama3-8b-8192"
    USE_GROQ_LLM: bool = True
    
    # Deepgram (40% cheaper than OpenAI Whisper)
    DEEPGRAM_API_KEY: Optional[str] = None
    DEEPGRAM_MODEL: str = "nova-2"
    USE_DEEPGRAM_STT: bool = True
    
    # ElevenLabs (Natural TTS)
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE: str = "Rachel"
    USE_ELEVENLABS_TTS: bool = True
    
    # OpenAI (Fallback)
    OPENAI_API_KEY: Optional[str] = None
    ENABLE_AI_FALLBACKS: bool = True
    
    # ===========================================
    # TWILIO
    # ===========================================
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_WEBHOOK_URL: Optional[str] = None
    
    # ===========================================
    # GOOGLE CALENDAR
    # ===========================================
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CALENDAR_ID: str = "primary"
    
    # ===========================================
    # REDIS & CELERY
    # ===========================================
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_WORKER_CONCURRENCY: int = 8
    
    # ===========================================
    # SECURITY
    # ===========================================
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # HIPAA Compliance
    ENCRYPTION_KEY: Optional[str] = None
    ADMIN_API_KEY: str = "admin-key-change-in-production"
    AUDIO_TOKEN_SECRET: str = "audio-token-secret-change"
    
    # ===========================================
    # MONITORING
    # ===========================================
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    
    # ===========================================
    # CORS & SECURITY
    # ===========================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # ===========================================
    # PERFORMANCE
    # ===========================================
    MAX_CONCURRENT_CALLS: int = 100
    RESPONSE_TIMEOUT_SECONDS: int = 30
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Fix postgres:// URLs for SQLAlchemy compatibility"""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings