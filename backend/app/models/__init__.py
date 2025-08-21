"""
Database models for VoiceAI 2.0
All models use async SQLAlchemy 2.0 patterns
"""

from app.models.tenant import Tenant
from app.models.customer import Customer
from app.models.call_log import CallLog
from app.models.system_config import SystemConfig
from app.models.voice_config import VoiceConfig
from app.models.appointment import Appointment

__all__ = [
    "Tenant",
    "Customer", 
    "CallLog",
    "SystemConfig",
    "VoiceConfig",
    "Appointment"
]