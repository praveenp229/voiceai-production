"""
Tenant service for multi-tenant operations
Handles tenant management, configuration, and validation
"""

from typing import Optional, List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import structlog

from app.models.tenant import Tenant
from app.models.voice_config import VoiceConfig
from app.models.system_config import SystemConfig, DEFAULT_CONFIGS

logger = structlog.get_logger(__name__)


class TenantService:
    """
    Service for tenant management operations
    
    Features:
    - Tenant CRUD operations
    - Voice configuration management
    - API key generation and validation
    - Default settings application
    """
    
    @staticmethod
    async def create_tenant(
        db: AsyncSession,
        name: str,
        email: str,
        phone: str = None,
        timezone: str = "America/Chicago",
        office_hours: Dict = None
    ) -> Tenant:
        """
        Create a new tenant with default configurations
        
        Args:
            db: Database session
            name: Tenant name (dental practice name)
            email: Contact email
            phone: Contact phone number
            timezone: Practice timezone
            office_hours: Office hours dictionary
            
        Returns:
            Created tenant object
        """
        try:
            logger.info("Creating new tenant", name=name, email=email)
            
            # Generate unique API key
            api_key = secrets.token_urlsafe(32)
            
            # Ensure unique email
            existing = await db.execute(select(Tenant).where(Tenant.email == email))
            if existing.scalar_one_or_none():
                raise ValueError(f"Tenant with email {email} already exists")
            
            # Create tenant
            tenant = Tenant(
                name=name,
                email=email,
                phone=phone,
                api_key=api_key,
                timezone=timezone,
                office_hours=str(office_hours) if office_hours else None
            )
            
            db.add(tenant)
            await db.flush()  # Get the tenant ID
            
            # Create default voice configuration
            await TenantService._create_default_voice_config(db, tenant.id)
            
            await db.commit()
            
            logger.info(
                "Tenant created successfully",
                tenant_id=tenant.id,
                name=name,
                api_key=f"{api_key[:8]}..."
            )
            
            return tenant
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create tenant", error=str(e), name=name, email=email)
            raise
    
    @staticmethod
    async def get_tenant_by_id(db: AsyncSession, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tenant_by_api_key(db: AsyncSession, api_key: str) -> Optional[Tenant]:
        """Get tenant by API key"""
        result = await db.execute(select(Tenant).where(Tenant.api_key == api_key))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_tenant_by_email(db: AsyncSession, email: str) -> Optional[Tenant]:
        """Get tenant by email"""
        result = await db.execute(select(Tenant).where(Tenant.email == email))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_tenants(
        db: AsyncSession,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Tenant]:
        """List all tenants with pagination"""
        query = select(Tenant)
        
        if active_only:
            query = query.where(Tenant.active == True)
        
        query = query.limit(limit).offset(offset).order_by(Tenant.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def update_tenant(
        db: AsyncSession,
        tenant_id: str,
        **updates
    ) -> Optional[Tenant]:
        """Update tenant information"""
        try:
            tenant = await TenantService.get_tenant_by_id(db, tenant_id)
            if not tenant:
                return None
            
            # Update allowed fields
            allowed_fields = ['name', 'email', 'phone', 'timezone', 'office_hours', 'active']
            for field, value in updates.items():
                if field in allowed_fields and hasattr(tenant, field):
                    setattr(tenant, field, value)
            
            await db.commit()
            
            logger.info("Tenant updated", tenant_id=tenant_id, updates=list(updates.keys()))
            return tenant
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update tenant", error=str(e), tenant_id=tenant_id)
            raise
    
    @staticmethod
    async def deactivate_tenant(db: AsyncSession, tenant_id: str) -> bool:
        """Deactivate a tenant (soft delete)"""
        try:
            tenant = await TenantService.get_tenant_by_id(db, tenant_id)
            if not tenant:
                return False
            
            tenant.active = False
            await db.commit()
            
            logger.info("Tenant deactivated", tenant_id=tenant_id)
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to deactivate tenant", error=str(e), tenant_id=tenant_id)
            raise
    
    @staticmethod
    async def regenerate_api_key(db: AsyncSession, tenant_id: str) -> Optional[str]:
        """Regenerate API key for tenant"""
        try:
            tenant = await TenantService.get_tenant_by_id(db, tenant_id)
            if not tenant:
                return None
            
            new_api_key = secrets.token_urlsafe(32)
            tenant.api_key = new_api_key
            await db.commit()
            
            logger.info("API key regenerated", tenant_id=tenant_id, new_key=f"{new_api_key[:8]}...")
            return new_api_key
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to regenerate API key", error=str(e), tenant_id=tenant_id)
            raise
    
    @staticmethod
    async def get_voice_config(db: AsyncSession, tenant_id: str) -> Optional[VoiceConfig]:
        """Get voice configuration for tenant"""
        result = await db.execute(
            select(VoiceConfig).where(VoiceConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_voice_config(
        db: AsyncSession,
        tenant_id: str,
        **updates
    ) -> Optional[VoiceConfig]:
        """Update voice configuration for tenant"""
        try:
            voice_config = await TenantService.get_voice_config(db, tenant_id)
            if not voice_config:
                # Create new voice config if it doesn't exist
                voice_config = await TenantService._create_default_voice_config(db, tenant_id)
            
            # Update allowed fields
            allowed_fields = [
                'ai_model', 'ai_temperature', 'ai_max_tokens',
                'voice_provider', 'voice_name', 'voice_speed', 'voice_stability',
                'response_style', 'greeting_style', 'personality',
                'primary_language', 'secondary_languages', 'auto_detect_language',
                'practice_name', 'practice_type', 'office_hours', 'booking_policy',
                'system_prompt', 'greeting_message', 'closing_message',
                'max_call_duration', 'enable_interruptions', 'confidence_threshold',
                'fallback_to_human', 'google_calendar_enabled', 'sms_confirmations',
                'email_confirmations'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields and hasattr(voice_config, field):
                    setattr(voice_config, field, value)
            
            await db.commit()
            
            logger.info("Voice config updated", tenant_id=tenant_id, updates=list(updates.keys()))
            return voice_config
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update voice config", error=str(e), tenant_id=tenant_id)
            raise
    
    @staticmethod
    async def validate_tenant_access(
        db: AsyncSession,
        tenant_id: str = None,
        api_key: str = None
    ) -> Optional[Tenant]:
        """
        Validate tenant access by ID or API key
        
        Args:
            db: Database session
            tenant_id: Tenant ID to validate
            api_key: API key to validate
            
        Returns:
            Tenant object if valid, None if invalid
        """
        if not tenant_id and not api_key:
            return None
        
        try:
            if api_key:
                tenant = await TenantService.get_tenant_by_api_key(db, api_key)
            else:
                tenant = await TenantService.get_tenant_by_id(db, tenant_id)
            
            if tenant and tenant.active:
                return tenant
            
            return None
            
        except Exception as e:
            logger.error("Tenant validation failed", error=str(e), tenant_id=tenant_id)
            return None
    
    @staticmethod
    async def _create_default_voice_config(
        db: AsyncSession,
        tenant_id: str
    ) -> VoiceConfig:
        """Create default voice configuration for new tenant"""
        
        # Get default values from system config
        default_configs = await TenantService._get_default_configs(db)
        
        voice_config = VoiceConfig(
            tenant_id=tenant_id,
            ai_model=default_configs.get('DEFAULT_AI_MODEL', 'gpt-4o-mini'),
            voice_provider=default_configs.get('DEFAULT_VOICE_PROVIDER', 'openai'),
            voice_name=default_configs.get('DEFAULT_VOICE_NAME', 'nova'),
            voice_speed=default_configs.get('DEFAULT_VOICE_SPEED', '1.0'),
            voice_stability=default_configs.get('DEFAULT_VOICE_STABILITY', '0.75'),
            confidence_threshold=default_configs.get('DEFAULT_CONFIDENCE_THRESHOLD', '0.7'),
            max_call_duration=int(default_configs.get('CALL_DURATION_LIMIT', '300')),
            sms_confirmations=default_configs.get('SMS_CONFIRMATIONS_ENABLED', 'true').lower() == 'true',
            google_calendar_enabled=default_configs.get('GOOGLE_CALENDAR_ENABLED', 'true').lower() == 'true'
        )
        
        db.add(voice_config)
        return voice_config
    
    @staticmethod
    async def _get_default_configs(db: AsyncSession) -> Dict[str, str]:
        """Get default configurations from system config"""
        try:
            result = await db.execute(select(SystemConfig))
            configs = result.scalars().all()
            
            config_dict = {config.key: config.value for config in configs}
            
            # Add hardcoded defaults for missing configs
            for key, config_data in DEFAULT_CONFIGS.items():
                if key not in config_dict:
                    config_dict[key] = config_data['value']
            
            return config_dict
            
        except Exception as e:
            logger.error("Failed to get default configs", error=str(e))
            # Return hardcoded defaults
            return {key: config_data['value'] for key, config_data in DEFAULT_CONFIGS.items()}
    
    @staticmethod
    async def get_tenant_stats(db: AsyncSession, tenant_id: str) -> Dict:
        """Get statistics for a tenant"""
        try:
            # This would typically involve complex queries
            # For now, return basic structure
            stats = {
                "tenant_id": tenant_id,
                "total_calls": 0,
                "successful_calls": 0,
                "appointments_scheduled": 0,
                "avg_call_duration": 0,
                "avg_response_time": 0,
                "cost_this_month": 0.0,
                "active_customers": 0
            }
            
            # TODO: Implement actual stats queries
            # These would involve joining with CallLog, Appointment, Customer tables
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get tenant stats", error=str(e), tenant_id=tenant_id)
            return {"error": str(e)}