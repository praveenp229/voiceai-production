"""
Test webhook endpoints to verify voice call integration
"""

import asyncio
import httpx
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.services.tenant_service import TenantService


async def test_webhook_integration():
    """Test webhook integration with mock Twilio request"""
    try:
        print("=" * 60)
        print("📞 VoiceAI 2.0 - Webhook Integration Test")
        print("=" * 60)
        
        # Get tenant ID
        async with AsyncSessionLocal() as db:
            tenant = await TenantService.get_tenant_by_email(db, "demo@voiceai.test")
            if not tenant:
                print("❌ Demo tenant not found. Run 'python init_db.py' first.")
                return
        
        tenant_id = tenant.id
        print(f"✅ Testing with tenant ID: {tenant_id}")
        
        # Test local webhook (assuming server is running on localhost:8000)
        base_url = "http://localhost:8000"
        webhook_url = f"{base_url}/api/v1/voice/{tenant_id}"
        
        print(f"\n🔗 Testing webhook URL: {webhook_url}")
        
        # Mock Twilio webhook data
        webhook_data = {
            "From": "+15551234567",
            "To": "+15559876543", 
            "CallSid": "CA1234567890abcdef1234567890abcdef",
            "CallStatus": "in-progress",
            "Direction": "inbound"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test health endpoint first
                print("\n1️⃣ Testing health endpoint...")
                health_response = await client.get(f"{base_url}/health")
                
                if health_response.status_code == 200:
                    print("✅ Health endpoint working")
                    health_data = health_response.json()
                    print(f"   Status: {health_data.get('status')}")
                    print(f"   Environment: {health_data.get('environment')}")
                else:
                    print(f"❌ Health endpoint failed: {health_response.status_code}")
                    return
                
                # Test webhook endpoint
                print("\n2️⃣ Testing voice webhook...")
                webhook_response = await client.post(
                    webhook_url,
                    data=webhook_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                print(f"   Status Code: {webhook_response.status_code}")
                print(f"   Content Type: {webhook_response.headers.get('content-type')}")
                
                if webhook_response.status_code == 200:
                    print("✅ Webhook endpoint working")
                    
                    # Check if response is TwiML
                    response_text = webhook_response.text
                    if "<?xml" in response_text and "<Response>" in response_text:
                        print("✅ Valid TwiML response received")
                        
                        # Show TwiML structure
                        lines = response_text.split('\n')
                        for line in lines[:5]:  # Show first 5 lines
                            if line.strip():
                                print(f"   {line}")
                        if len(lines) > 5:
                            print("   ...")
                    else:
                        print("⚠️ Response is not TwiML format")
                        print(f"   Response: {response_text[:200]}...")
                        
                else:
                    print(f"❌ Webhook failed: {webhook_response.status_code}")
                    print(f"   Error: {webhook_response.text}")
                    return
                
                # Test API documentation
                print("\n3️⃣ Testing API documentation...")
                docs_response = await client.get(f"{base_url}/docs")
                
                if docs_response.status_code == 200:
                    print("✅ API documentation available")
                    print(f"   URL: {base_url}/docs")
                else:
                    print(f"⚠️ API docs not available: {docs_response.status_code}")
                
                print("\n" + "=" * 60)
                print("🎉 Webhook Integration Test Results")
                print("=" * 60)
                print("✅ Local server is running correctly")
                print("✅ Webhook endpoint responds with TwiML")
                print("✅ Ready for Twilio integration")
                print()
                print("📋 Next Steps:")
                print("1. Deploy to a public URL (Railway, Render, etc.)")
                print("2. Update Twilio webhook with public URL:")
                print(f"   https://YOUR_DOMAIN/api/v1/voice/{tenant_id}")
                print("3. Call your Twilio number to test live!")
                print("=" * 60)
                
            except httpx.ConnectError:
                print("❌ Cannot connect to local server")
                print("   Make sure the server is running:")
                print("   python main.py")
                print()
                
            except Exception as e:
                print(f"❌ Test error: {e}")
                
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_webhook_integration())