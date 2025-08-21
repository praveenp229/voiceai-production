"""
Database initialization script
Creates all tables and initial data for VoiceAI 2.0
"""

import asyncio
import os
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

from app.core.database import init_db, AsyncSessionLocal
from app.services.tenant_service import TenantService
from app.models.system_config import SystemConfig, DEFAULT_CONFIGS
import structlog

logger = structlog.get_logger(__name__)


async def initialize_database():
    """Initialize database with tables and default data"""
    try:
        print("🗄️  Initializing VoiceAI 2.0 database...")
        
        # Create all tables
        await init_db()
        print("✅ Database tables created")
        
        # Add default system configurations
        await add_default_configs()
        print("✅ Default configurations added")
        
        # Create demo tenant
        await create_demo_tenant()
        print("✅ Demo tenant created")
        
        print("\n🎉 Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def add_default_configs():
    """Add default system configurations"""
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            
            # Check if configs already exist
            result = await db.execute(select(SystemConfig))
            existing_configs = result.scalars().all()
            existing_keys = {config.key for config in existing_configs}
            
            # Add missing default configs
            for key, config_data in DEFAULT_CONFIGS.items():
                if key not in existing_keys:
                    config = SystemConfig(
                        key=key,
                        value=config_data["value"],
                        description=config_data["description"],
                        category=config_data["category"],
                        is_public=config_data.get("is_public", False)
                    )
                    db.add(config)
            
            await db.commit()
            logger.info("Default configurations added")
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to add default configs", error=str(e))
            raise


async def create_demo_tenant():
    """Create a demo tenant for testing"""
    async with AsyncSessionLocal() as db:
        try:
            # Check if demo tenant already exists
            existing_tenant = await TenantService.get_tenant_by_email(db, "demo@voiceai.test")
            
            if not existing_tenant:
                # Create demo tenant
                tenant = await TenantService.create_tenant(
                    db=db,
                    name="Demo Dental Practice",
                    email="demo@voiceai.test",
                    phone="+1234567890",
                    timezone="America/New_York"
                )
                
                print(f"📋 Demo tenant created:")
                print(f"   ID: {tenant.id}")
                print(f"   API Key: {tenant.api_key}")
                print(f"   Email: {tenant.email}")
                
                # Update voice config for demo
                await TenantService.update_voice_config(
                    db=db,
                    tenant_id=tenant.id,
                    practice_name="Demo Dental Practice",
                    greeting_message="Thank you for calling Demo Dental Practice! I'm your AI assistant. How can I help you schedule your appointment today?",
                    response_style="friendly",
                    voice_name="nova"
                )
                
                print(f"✅ Demo tenant voice config updated")
            else:
                print(f"📋 Demo tenant already exists:")
                print(f"   ID: {existing_tenant.id}")
                print(f"   API Key: {existing_tenant.api_key}")
                
        except Exception as e:
            logger.error("Failed to create demo tenant", error=str(e))
            raise


async def main():
    """Main initialization function"""
    print("=" * 60)
    print("🚀 VoiceAI 2.0 Database Initialization")
    print("=" * 60)
    
    await initialize_database()


if __name__ == "__main__":
    asyncio.run(main())