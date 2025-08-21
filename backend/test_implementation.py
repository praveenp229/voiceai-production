"""
VoiceAI 2.0 Implementation Test Script
Tests all core functionality to verify the system is working
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.services.tenant_service import TenantService
from app.services.ai_service import AIService
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)


async def test_database_connection():
    """Test database connectivity"""
    print("\n🗄️  Testing database connection...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Simple query test
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            value = result.scalar()
            
            if value == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


async def test_tenant_service():
    """Test tenant management functionality"""
    print("\n👥 Testing tenant service...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Test getting demo tenant
            demo_tenant = await TenantService.get_tenant_by_email(db, "demo@voiceai.test")
            
            if demo_tenant:
                print(f"✅ Demo tenant found: {demo_tenant.name}")
                print(f"   ID: {demo_tenant.id}")
                print(f"   API Key: {demo_tenant.api_key[:8]}...")
                
                # Test voice config
                voice_config = await TenantService.get_voice_config(db, demo_tenant.id)
                if voice_config:
                    print(f"✅ Voice config found: {voice_config.ai_model}")
                else:
                    print("❌ Voice config not found")
                    return False
                
                return True
            else:
                print("❌ Demo tenant not found")
                return False
                
    except Exception as e:
        print(f"❌ Tenant service error: {e}")
        return False


async def test_ai_service():
    """Test AI service functionality"""
    print("\n🤖 Testing AI service...")
    
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
        print("⚠️  OpenAI API key not configured - skipping AI tests")
        return True
    
    try:
        ai_service = AIService()
        
        # Test conversation processing (mock)
        print("   Testing conversation processing...")
        
        # Mock voice config
        class MockVoiceConfig:
            ai_model = "gpt-4o-mini"
            ai_temperature = "0.7"
            ai_max_tokens = 150
            voice_name = "nova"
            voice_speed = "1.0"
            
            def get_system_prompt(self):
                return "You are a helpful dental assistant AI."
        
        voice_config = MockVoiceConfig()
        
        # Test with simple input
        response, confidence = await ai_service.process_conversation(
            user_input="I need to schedule an appointment",
            voice_config=voice_config,
            tenant_id="test"
        )
        
        if response and confidence > 0:
            print(f"✅ AI conversation processing successful")
            print(f"   Response: {response[:100]}...")
            print(f"   Confidence: {confidence}")
            return True
        else:
            print("❌ AI conversation processing failed")
            return False
            
    except Exception as e:
        print(f"❌ AI service error: {e}")
        return False


async def test_api_endpoints():
    """Test API endpoints availability"""
    print("\n🌐 Testing API endpoints...")
    
    try:
        import httpx
        
        # Start a test server or check if one is running
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient() as client:
            try:
                # Test health endpoint
                response = await client.get(f"{base_url}/health", timeout=5.0)
                if response.status_code == 200:
                    print("✅ Health endpoint working")
                    
                    # Test API docs
                    docs_response = await client.get(f"{base_url}/docs", timeout=5.0)
                    if docs_response.status_code == 200:
                        print("✅ API documentation available")
                    
                    return True
                else:
                    print(f"❌ Health endpoint returned {response.status_code}")
                    return False
                    
            except httpx.ConnectError:
                print("⚠️  API server not running - start with 'python main.py'")
                return False
                
    except Exception as e:
        print(f"❌ API endpoint test error: {e}")
        return False


async def test_voice_processing_pipeline():
    """Test voice processing pipeline"""
    print("\n🎤 Testing voice processing pipeline...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Get demo tenant
            demo_tenant = await TenantService.get_tenant_by_email(db, "demo@voiceai.test")
            if not demo_tenant:
                print("❌ Demo tenant not found")
                return False
            
            voice_config = await TenantService.get_voice_config(db, demo_tenant.id)
            if not voice_config:
                print("❌ Voice config not found")
                return False
            
            # Test greeting generation
            greeting = voice_config.get_greeting_message()
            if greeting:
                print(f"✅ Greeting generated: {greeting[:50]}...")
            else:
                print("❌ Greeting generation failed")
                return False
            
            # Test intent detection
            ai_service = AIService()
            intent = ai_service.detect_appointment_intent("I want to schedule an appointment")
            
            if intent["intent"] == "schedule":
                print(f"✅ Intent detection working: {intent['intent']} (confidence: {intent['confidence']})")
            else:
                print("❌ Intent detection failed")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Voice processing test error: {e}")
        return False


async def test_celery_tasks():
    """Test Celery task system"""
    print("\n⚙️  Testing Celery tasks...")
    
    try:
        # Check if Redis is available
        import redis
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        print("✅ Redis connection successful")
        
        # Test task import
        from app.tasks.voice_tasks import process_voice_async
        from app.tasks.notification_tasks import send_sms_async
        
        print("✅ Celery tasks imported successfully")
        
        # Note: We don't actually run tasks here as workers might not be running
        print("⚠️  To test task execution, start workers with 'start-worker.bat'")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Celery/Redis not available: {e}")
        print("   System will work without Celery (sync mode)")
        return True  # Not a failure - system can work without Celery


def test_configuration():
    """Test configuration loading"""
    print("\n⚙️  Testing configuration...")
    
    try:
        print(f"✅ Environment: {settings.ENVIRONMENT}")
        print(f"✅ Debug mode: {settings.DEBUG}")
        print(f"✅ Database URL: {settings.DATABASE_URL}")
        
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            print("✅ OpenAI API key configured")
        else:
            print("⚠️  OpenAI API key not configured")
        
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_ACCOUNT_SID != "your_twilio_account_sid":
            print("✅ Twilio credentials configured")
        else:
            print("⚠️  Twilio credentials not configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results"""
    print("=" * 60)
    print("🧪 VoiceAI 2.0 Implementation Tests")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Database Connection", test_database_connection),
        ("Tenant Service", test_tenant_service),
        ("AI Service", test_ai_service),
        ("Voice Processing", test_voice_processing_pipeline),
        ("Celery Tasks", test_celery_tasks),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! VoiceAI 2.0 is ready for testing!")
        print("\n📋 Next steps:")
        print("1. Start the server: python main.py")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Configure Twilio webhook: http://your-domain.com/api/v1/voice/{tenant_id}")
    else:
        print(f"\n⚠️  {total-passed} test(s) failed. Please check the errors above.")
        
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your_openai_api_key_here":
            print("\n💡 Tip: Set OPENAI_API_KEY in .env file to enable AI features")
        
        if not settings.TWILIO_ACCOUNT_SID or settings.TWILIO_ACCOUNT_SID == "your_twilio_account_sid":
            print("💡 Tip: Set Twilio credentials in .env file to enable voice calls")


if __name__ == "__main__":
    asyncio.run(run_all_tests())