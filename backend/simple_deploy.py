"""
Simple Railway deployment version - Twilio integration embedded
"""

import os
from fastapi import FastAPI, Form, Depends, HTTPException, status
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging
import re
import openai
import jwt
import hashlib
import uuid
from pydantic import BaseModel

# Twilio imports
try:
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Warning: Twilio not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI
openai_client = None
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    try:
        openai_client = openai.OpenAI(api_key=openai_api_key)
        logger.info("OpenAI client initialized")
    except Exception as e:
        logger.error(f"OpenAI initialization failed: {e}")

# Twilio setup
twilio_client = None
if TWILIO_AVAILABLE:
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    if account_sid and auth_token:
        try:
            twilio_client = Client(account_sid, auth_token)
            logger.info("Twilio client initialized")
        except Exception as e:
            logger.error(f"Twilio initialization failed: {e}")

# JWT Secret
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")

# Create FastAPI app
app = FastAPI(title="VoiceAI SaaS Platform", version="6.1.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
tenants = {}
appointments = {}
call_logs = {}
admin_users = {
    "admin@voiceai.com": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "super_admin",
        "name": "Platform Admin"
    }
}
tenant_users = {}

# Sample data initialization
def initialize_sample_data():
    """Initialize sample tenants and users"""
    global tenants, tenant_users
    
    # Sample tenants
    tenants = {
        "tenant_0001": {
            "id": "tenant_0001",
            "name": "Demo Dental Practice",
            "contact_email": "admin@demodental.com",
            "phone": "+1-555-0123",
            "plan": "premium",
            "status": "active",
            "created_at": "2024-01-15T10:00:00Z",
            "monthly_fee": 99.99
        },
        "tenant_0002": {
            "id": "tenant_0002", 
            "name": "Smile Care Clinic",
            "contact_email": "admin@smilecare.com",
            "phone": "+1-555-0124",
            "plan": "basic",
            "status": "active",
            "created_at": "2024-01-16T11:00:00Z",
            "monthly_fee": 49.99
        }
    }
    
    # Sample tenant users
    tenant_users = {
        "admin@demodental.com": {
            "email": "admin@demodental.com",
            "password_hash": hashlib.sha256("temp123".encode()).hexdigest(),
            "tenant_id": "tenant_0001",
            "role": "tenant_admin",
            "name": "Demo Admin"
        },
        "admin@smilecare.com": {
            "email": "admin@smilecare.com", 
            "password_hash": hashlib.sha256("temp123".encode()).hexdigest(),
            "tenant_id": "tenant_0002",
            "role": "tenant_admin",
            "name": "Smile Admin"
        }
    }

# Pydantic Models
class LoginRequest(BaseModel):
    email: str
    password: str
    user_type: str

# Security
security = HTTPBearer()

def create_jwt_token(user_data: dict, expires_hours: int = 24) -> str:
    """Create JWT token"""
    payload = {
        **user_data,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get admin user from token"""
    payload = verify_jwt_token(credentials.credentials)
    if payload.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload

def get_tenant_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get tenant user from token"""
    payload = verify_jwt_token(credentials.credentials)
    if payload.get("user_type") != "tenant":
        raise HTTPException(status_code=403, detail="Tenant access required")
    return payload

# Twilio webhook endpoints
@app.post("/api/v1/twilio/voice")
async def twilio_voice_webhook(
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    tenant_id: Optional[str] = Form(None)
):
    """Handle incoming Twilio voice calls"""
    try:
        logger.info(f"Incoming call: {CallSid} from {From} to {To}")
        
        # Store call information
        call_data = {
            "call_sid": CallSid,
            "from_number": From,
            "to_number": To,
            "tenant_id": tenant_id,
            "call_type": "inbound",
            "call_status": "in-progress",
            "start_time": datetime.now().isoformat(),
            "ai_processed": False
        }
        
        # Add to call logs
        call_logs[CallSid] = call_data
        
        # Generate TwiML response
        response = VoiceResponse()
        
        greeting = """
        Hello! Thank you for calling our dental practice. 
        I'm your AI assistant and I'll help you schedule an appointment today.
        Please tell me your name, phone number, and when you'd like to come in.
        I'll be recording this call to ensure we get all your details correctly.
        Please speak after the beep.
        """
        
        response.say(greeting, voice='alice', language='en-US')
        
        # Record the call
        webhook_base_url = os.getenv('WEBHOOK_BASE_URL', 'https://voiceai-backend-production-81d6.up.railway.app')
        record_url = f"{webhook_base_url}/api/v1/twilio/recording"
        if tenant_id:
            record_url += f"?tenant_id={tenant_id}"
            
        response.record(
            action=record_url,
            method='POST',
            max_length=300,
            finish_on_key='#',
            transcribe=True,
            transcribe_callback=f"{webhook_base_url}/api/v1/twilio/transcription"
        )
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in voice webhook: {e}")
        response = VoiceResponse()
        response.say("Sorry, we're experiencing technical difficulties. Please try again later.")
        return Response(content=str(response), media_type="application/xml")

@app.post("/api/v1/twilio/recording")
async def twilio_recording_webhook(
    CallSid: str = Form(...),
    RecordingSid: str = Form(...),
    RecordingUrl: str = Form(...),
    RecordingDuration: int = Form(...),
    tenant_id: Optional[str] = Form(None)
):
    """Handle recording completion"""
    try:
        logger.info(f"Recording completed: {RecordingSid} for call {CallSid}")
        
        # Update call log with recording info
        if CallSid in call_logs:
            call_logs[CallSid].update({
                "recording_sid": RecordingSid,
                "recording_url": RecordingUrl,
                "recording_duration": RecordingDuration,
                "call_status": "completed"
            })
        
        response = VoiceResponse()
        response.say("Thank you! We've recorded your information and will call you back shortly to confirm your appointment.")
        response.hangup()
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in recording webhook: {e}")
        response = VoiceResponse()
        response.say("Thank you for calling. Have a great day!")
        return Response(content=str(response), media_type="application/xml")

@app.post("/api/v1/twilio/transcription")
async def twilio_transcription_webhook(
    CallSid: str = Form(...),
    TranscriptionSid: str = Form(...),
    TranscriptionText: str = Form(...),
    TranscriptionStatus: str = Form(...),
    tenant_id: Optional[str] = Form(None)
):
    """Handle transcription completion"""
    try:
        logger.info(f"Transcription completed: {TranscriptionSid} for call {CallSid}")
        
        # Update call log with transcription
        if CallSid in call_logs:
            call_logs[CallSid].update({
                "transcription_sid": TranscriptionSid,
                "transcript": TranscriptionText,
                "transcription_status": TranscriptionStatus
            })
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error in transcription webhook: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/v1/twilio/status")
async def twilio_status_webhook(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    From: str = Form(None),
    To: str = Form(None),
    CallDuration: Optional[int] = Form(None)
):
    """Handle call status updates"""
    try:
        logger.info(f"Call status update: {CallSid} - {CallStatus}")
        
        # Update call log with status
        if CallSid in call_logs:
            call_logs[CallSid].update({
                "call_status": CallStatus,
                "call_duration": CallDuration,
                "end_time": datetime.now().isoformat() if CallStatus == "completed" else None
            })
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error in status webhook: {e}")
        return {"success": False, "error": str(e)}

# Auth endpoints
@app.post("/api/v1/auth/login")
async def login_v1(login_data: LoginRequest):
    """Login endpoint (v1)"""
    try:
        email = login_data.email.lower().strip()
        password = login_data.password
        user_type = login_data.user_type
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if user_type == "admin":
            if email in admin_users and admin_users[email]["password_hash"] == password_hash:
                user_data = {
                    "email": email,
                    "user_type": "admin",
                    "role": admin_users[email]["role"],
                    "name": admin_users[email]["name"]
                }
                token = create_jwt_token(user_data)
                
                return {
                    "success": True,
                    "token": token,
                    "user_type": "admin",
                    "name": admin_users[email]["name"],
                    "email": email
                }
        
        elif user_type == "tenant":
            if email in tenant_users and tenant_users[email]["password_hash"] == password_hash:
                user_data = {
                    "email": email,
                    "user_type": "tenant", 
                    "tenant_id": tenant_users[email]["tenant_id"],
                    "role": tenant_users[email]["role"],
                    "name": tenant_users[email]["name"]
                }
                token = create_jwt_token(user_data)
                
                return {
                    "success": True,
                    "token": token,
                    "user_type": "tenant",
                    "name": tenant_users[email]["name"],
                    "email": email,
                    "tenant_id": tenant_users[email]["tenant_id"]
                }
        
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# Call logs endpoint
@app.get("/api/v1/tenant/{tenant_id}/calls")
async def get_tenant_calls_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get calls for a tenant (v1 endpoint)"""
    try:
        # Filter calls for this tenant
        tenant_calls = []
        for call_id, call_data in call_logs.items():
            if call_data.get("tenant_id") == tenant_id or tenant_id == "default":
                tenant_calls.append({
                    "id": call_id,
                    "caller_phone": call_data.get("from_number"),
                    "call_duration": f"{call_data.get('recording_duration', 0)} seconds",
                    "call_type": call_data.get("call_type", "inbound"),
                    "call_status": call_data.get("call_status", "unknown"),
                    "transcript": call_data.get("transcript", ""),
                    "ai_processed": call_data.get("ai_processed", False),
                    "ai_analysis": call_data.get("ai_analysis", {}),
                    "appointment_created": call_data.get("appointment_created", False),
                    "created_at": call_data.get("start_time", "")
                })
        
        # Sort by creation time (most recent first)
        tenant_calls.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "success": True,
            "calls": tenant_calls[:50]  # Limit to 50 most recent
        }
        
    except Exception as e:
        logger.error(f"Error getting calls: {e}")
        raise HTTPException(status_code=500, detail="Failed to get calls")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "service": "VoiceAI SaaS Platform", 
            "version": "6.1.0",
            "timestamp": datetime.now().isoformat(),
            "features": {
                "voice_ai": openai_client is not None,
                "twilio_integration": twilio_client is not None,
                "multi_tenant": True,
                "total_tenants": len(tenants),
                "total_calls": len(call_logs)
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Initialize sample data when server starts
initialize_sample_data()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting VoiceAI SaaS Platform v6.1.0 on port {port}")
    print(f"Twilio Integration: {'✅ Enabled' if twilio_client else '❌ Disabled'}")
    print("Demo Credentials:")
    print("  Super Admin: admin@voiceai.com / admin123")
    print("  Tenant 1: admin@demodental.com / temp123")
    print("  Tenant 2: admin@smilecare.com / temp123")
    uvicorn.run(app, host="0.0.0.0", port=port)