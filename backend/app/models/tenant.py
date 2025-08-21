"""
Tenant model for multi-tenant architecture
Each tenant represents a dental hospital/practice
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Tenant(Base):
    """
    Tenant model for multi-tenant dental practices
    
    Each tenant has:
    - Unique API key for authentication
    - Custom voice configurations
    - Separate call logs and customers
    - Timezone and office hours settings
    """
    __tablename__ = "tenants"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic information
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True)
    
    # Authentication
    api_key = Column(String(64), nullable=False, unique=True, index=True)
    
    # Settings
    timezone = Column(String(50), default="America/Chicago")
    office_hours = Column(Text, nullable=True)  # JSON string
    
    # Status
    active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    voice_config = relationship("VoiceConfig", back_populates="tenant", uselist=False)
    customers = relationship("Customer", back_populates="tenant", lazy="dynamic")
    call_logs = relationship("CallLog", back_populates="tenant", lazy="dynamic")
    appointments = relationship("Appointment", back_populates="tenant", lazy="dynamic")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_tenant_active_created", "active", "created_at"),
        Index("idx_tenant_email_active", "email", "active"),
    )
    
    def __repr__(self):
        return f"<Tenant(id='{self.id}', name='{self.name}', active={self.active})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "timezone": self.timezone,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }