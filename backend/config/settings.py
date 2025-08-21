"""
Production-ready configuration system for VoiceAI 2.0
Handles all environment variables with proper validation and defaults
"""

import os
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from functools import lru_cache
import json


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(default="sqlite+aiosqlite:///./voiceai.db")
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=30)
    echo: bool = Field(default=False)
    
    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v):
        """Fix postgres:// URLs for SQLAlchemy compatibility"""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v


class OpenAIConfig(BaseModel):
    """OpenAI API configuration"""
    api_key: Optional[str] = Field(default=None)
    model: str = Field(default="gpt-4o-mini")
    max_tokens: int = Field(default=150)
    temperature: float = Field(default=0.7)
    timeout: int = Field(default=30)
    
    @property
    def is_configured(self) -> bool:
        return self.api_key is not None and self.api_key != "your_openai_api_key_here"


class TwilioConfig(BaseModel):
    """Twilio configuration"""
    account_sid: Optional[str] = Field(default=None)
    auth_token: Optional[str] = Field(default=None)
    phone_number: Optional[str] = Field(default=None)
    webhook_timeout: int = Field(default=10)
    
    @property
    def is_configured(self) -> bool:
        return all([
            self.account_sid and self.account_sid != "your_twilio_account_sid",
            self.auth_token and self.auth_token != "your_twilio_auth_token",
            self.phone_number
        ])


class RedisConfig(BaseModel):
    """Redis/Celery configuration"""
    url: str = Field(default="redis://localhost:6379/0")
    broker_url: str = Field(default="redis://localhost:6379/0")
    result_backend: str = Field(default="redis://localhost:6379/0")
    
    @property
    def is_available(self) -> bool:
        try:
            import redis
            r = redis.Redis.from_url(self.url)
            r.ping()
            return True
        except:
            return False


class SecurityConfig(BaseModel):
    """Security configuration"""
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    jwt_secret: str = Field(default="jwt-secret-for-development")
    admin_api_key: str = Field(default="admin-dev-key")
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"])
    cors_origins: List[str] = Field(default=["http://localhost:3000"])
    
    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


class VoiceAISettings(BaseModel):
    """Main VoiceAI configuration"""
    
    # Basic app settings
    app_name: str = Field(default="VoiceAI 2.0")
    version: str = Field(default="2.0.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    twilio: TwilioConfig = Field(default_factory=TwilioConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Feature flags
    enable_conversation_relay: bool = Field(default=False)
    enable_calendar_integration: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)
    enable_logging: bool = Field(default=True)
    
    # Performance settings
    max_concurrent_calls: int = Field(default=100)
    response_timeout: int = Field(default=30)
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    @property
    def system_status(self) -> dict:
        """Get system configuration status"""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "openai_configured": self.openai.is_configured,
            "twilio_configured": self.twilio.is_configured,
            "redis_available": self.redis.is_available,
            "conversation_relay_enabled": self.enable_conversation_relay,
            "calendar_integration": self.enable_calendar_integration
        }


def load_settings_from_env() -> VoiceAISettings:
    """Load settings from environment variables"""
    
    # Build configuration from environment
    config_data = {
        "app_name": os.getenv("APP_NAME", "VoiceAI 2.0"),
        "version": os.getenv("VERSION", "2.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "true").lower() == "true",
        
        "database": {
            "url": os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./voiceai.db"),
            "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "20")),
            "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "30")),
            "echo": os.getenv("DATABASE_ECHO", "false").lower() == "true"
        },
        
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "150")),
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            "timeout": int(os.getenv("OPENAI_TIMEOUT", "30"))
        },
        
        "twilio": {
            "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
            "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
            "phone_number": os.getenv("TWILIO_PHONE_NUMBER"),
            "webhook_timeout": int(os.getenv("TWILIO_WEBHOOK_TIMEOUT", "10"))
        },
        
        "redis": {
            "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "broker_url": os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        },
        
        "security": {
            "secret_key": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
            "jwt_secret": os.getenv("JWT_SECRET_KEY", "jwt-secret-for-development"),
            "admin_api_key": os.getenv("ADMIN_API_KEY", "admin-dev-key"),
            "allowed_hosts": os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1"),
            "cors_origins": os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
        },
        
        "enable_conversation_relay": os.getenv("ENABLE_CONVERSATION_RELAY", "false").lower() == "true",
        "enable_calendar_integration": os.getenv("ENABLE_CALENDAR_INTEGRATION", "true").lower() == "true",
        "enable_metrics": os.getenv("ENABLE_METRICS", "true").lower() == "true",
        "enable_logging": os.getenv("ENABLE_LOGGING", "true").lower() == "true",
        
        "max_concurrent_calls": int(os.getenv("MAX_CONCURRENT_CALLS", "100")),
        "response_timeout": int(os.getenv("RESPONSE_TIMEOUT", "30"))
    }
    
    return VoiceAISettings(**config_data)


@lru_cache()
def get_settings() -> VoiceAISettings:
    """Get cached settings instance"""
    return load_settings_from_env()


def validate_production_config(settings: VoiceAISettings) -> List[str]:
    """Validate configuration for production deployment"""
    issues = []
    
    if settings.is_production:
        # Security checks
        if settings.security.secret_key == "dev-secret-key-change-in-production":
            issues.append("SECRET_KEY must be changed for production")
        
        if settings.security.jwt_secret == "jwt-secret-for-development":
            issues.append("JWT_SECRET_KEY must be changed for production")
        
        if settings.debug:
            issues.append("DEBUG should be False in production")
        
        # Service checks
        if not settings.openai.is_configured:
            issues.append("OpenAI API key not configured")
        
        if not settings.twilio.is_configured:
            issues.append("Twilio credentials not configured")
    
    return issues


def print_config_summary(settings: VoiceAISettings):
    """Print configuration summary"""
    print("=" * 60)
    print(f"{settings.app_name} v{settings.version}")
    print("=" * 60)
    print(f"Environment: {settings.environment}")
    print(f"Debug: {settings.debug}")
    print(f"OpenAI: {'Configured' if settings.openai.is_configured else 'Not configured'}")
    print(f"Twilio: {'Configured' if settings.twilio.is_configured else 'Not configured'}")
    print(f"Redis: {'Available' if settings.redis.is_available else 'Not available'}")
    print(f"ConversationRelay: {'Enabled' if settings.enable_conversation_relay else 'Disabled'}")
    print(f"Calendar: {'Enabled' if settings.enable_calendar_integration else 'Disabled'}")
    
    # Production validation
    if settings.is_production:
        issues = validate_production_config(settings)
        if issues:
            print("\nProduction Issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("\nProduction configuration valid")
    
    print("=" * 60)


# Global settings instance
settings = get_settings()


if __name__ == "__main__":
    # Test configuration loading
    test_settings = get_settings()
    print_config_summary(test_settings)
    
    print(f"\nSystem Status:")
    for key, value in test_settings.system_status.items():
        print(f"  {key}: {value}")