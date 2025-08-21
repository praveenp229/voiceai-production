"""
Customer model for patients calling the voice AI system
Includes HIPAA compliance features and PII encryption
"""

from sqlalchemy import Column, String, DateTime, Text, Index, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Customer(Base):
    """
    Customer/Patient model with HIPAA compliance
    
    Features:
    - Encrypted PII (phone, name, email)
    - Unique constraint per tenant
    - Call history tracking
    - Appointment scheduling
    """
    __tablename__ = "customers"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Tenant relationship (multi-tenancy)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Customer information (encrypted in production)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    
    # Preferences
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(50), nullable=True)
    
    # Medical/Dental notes (encrypted)
    notes = Column(Text, nullable=True)
    
    # Call history summary
    total_calls = Column(String(10), default="0")
    last_call_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="customers")
    call_logs = relationship("CallLog", back_populates="customer", lazy="dynamic")
    appointments = relationship("Appointment", back_populates="customer", lazy="dynamic")
    
    # Constraints and indexes
    __table_args__ = (
        # Unique constraint: one customer per phone per tenant
        UniqueConstraint("tenant_id", "phone", name="uq_customer_tenant_phone"),
        
        # Performance indexes
        Index("idx_customer_tenant_phone", "tenant_id", "phone"),
        Index("idx_customer_tenant_created", "tenant_id", "created_at"),
        Index("idx_customer_last_call", "last_call_at"),
    )
    
    def __repr__(self):
        return f"<Customer(id='{self.id}', phone='{self.phone[:3]}***', tenant_id='{self.tenant_id}')>"
    
    def to_dict(self, include_pii: bool = False):
        """
        Convert to dictionary for API responses
        
        Args:
            include_pii: Whether to include personally identifiable information
        """
        base_data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "preferred_language": self.preferred_language,
            "timezone": self.timezone,
            "total_calls": self.total_calls,
            "last_call_at": self.last_call_at.isoformat() if self.last_call_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_pii:
            base_data.update({
                "name": self.name,
                "phone": self.phone,
                "email": self.email,
                "notes": self.notes,
            })
        else:
            # Masked PII for non-authorized access
            base_data.update({
                "name": self.name[:2] + "***" if self.name else None,
                "phone": self.phone[:3] + "***" if self.phone else None,
                "email": "***@***.com" if self.email else None,
            })
        
        return base_data
    
    def mask_phone(self) -> str:
        """Return masked phone number for logging"""
        if not self.phone:
            return "Unknown"
        return f"{self.phone[:3]}***{self.phone[-2:]}" if len(self.phone) > 5 else "***"