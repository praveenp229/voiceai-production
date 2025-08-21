"""
Quick script to get tenant information for webhook configuration
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.services.tenant_service import TenantService


async def get_tenant_info():
    """Get tenant information for webhook setup"""
    try:
        async with AsyncSessionLocal() as db:
            # Get demo tenant
            tenant = await TenantService.get_tenant_by_email(db, "demo@voiceai.test")
            
            if tenant:
                print("=" * 60)
                print("🔑 VoiceAI 2.0 - Tenant Information")
                print("=" * 60)
                print(f"Tenant ID: {tenant.id}")
                print(f"Name: {tenant.name}")
                print(f"Email: {tenant.email}")
                print(f"API Key: {tenant.api_key}")
                print(f"Phone: {tenant.phone}")
                print()
                print("📱 Twilio Webhook Configuration:")
                print(f"   Replace YOUR_DOMAIN with your actual domain")
                print(f"   https://YOUR_DOMAIN/api/v1/voice/{tenant.id}")
                print()
                print("🔗 Example URLs:")
                print(f"   Railway: https://voiceai-production.up.railway.app/api/v1/voice/{tenant.id}")
                print(f"   Render:  https://voiceai-app.onrender.com/api/v1/voice/{tenant.id}")
                print(f"   Ngrok:   https://abc123.ngrok.io/api/v1/voice/{tenant.id}")
                print()
                print("💡 Copy the webhook URL to your Twilio phone number configuration!")
                print("=" * 60)
            else:
                print("❌ Demo tenant not found. Run 'python init_db.py' first.")
                
    except Exception as e:
        print(f"❌ Error getting tenant info: {e}")


if __name__ == "__main__":
    asyncio.run(get_tenant_info())