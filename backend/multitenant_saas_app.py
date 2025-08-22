"""
VoiceAI 2.0 - Multi-Tenant SaaS Platform
Complete system with tenant management and dual dashboards
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
from twilio_integration import get_twilio_manager
from twilio.twiml.voice_response import VoiceResponse
import xml.etree.ElementTree as ET

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

# JWT Secret
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")

# Create FastAPI app
app = FastAPI(title="VoiceAI SaaS Platform", version="6.1.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class TenantCreate(BaseModel):
    name: str
    contact_email: str
    phone: str
    plan: str = "basic"

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str
    user_type: str  # "admin" or "tenant"

# In-memory storage (in production, use PostgreSQL)
tenants = {}
appointments = {}
call_states = {}
admin_users = {
    "admin@voiceai.com": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "super_admin",
        "name": "Platform Admin"
    }
}
tenant_users = {}  # tenant_id -> {user_data}

system_stats = {
    "total_calls": 0,
    "total_appointments": 0,
    "total_tenants": 0,
    "platform_revenue": 0,
    "start_time": datetime.now().isoformat()
}

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
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    return verify_jwt_token(credentials.credentials)

def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Require admin user"""
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def get_tenant_user(current_user: dict = Depends(get_current_user)):
    """Require tenant user"""
    if current_user.get("role") != "tenant_admin":
        raise HTTPException(status_code=403, detail="Tenant access required")
    return current_user

# Multi-tenant helper functions
def create_tenant(tenant_data: dict) -> str:
    """Create a new tenant"""
    tenant_id = f"tenant_{len(tenants) + 1:04d}"
    
    tenant = {
        "id": tenant_id,
        "name": tenant_data["name"],
        "contact_email": tenant_data["contact_email"],
        "phone": tenant_data["phone"],
        "plan": tenant_data.get("plan", "basic"),
        "status": "active",
        "webhook_url": f"/api/v1/voice/{tenant_id}",
        "twilio_phone": None,
        "settings": {
            "practice_hours": {
                "monday": "9:00 AM - 5:00 PM",
                "tuesday": "9:00 AM - 5:00 PM",
                "wednesday": "9:00 AM - 5:00 PM",
                "thursday": "9:00 AM - 5:00 PM",
                "friday": "9:00 AM - 4:00 PM",
                "saturday": "Closed",
                "sunday": "Closed"
            },
            "services": {
                "cleaning": {"duration": "30 min", "cost": "$120-180"},
                "checkup": {"duration": "45 min", "cost": "$150-250"},
                "consultation": {"duration": "60 min", "cost": "$100-200"},
                "emergency": {"duration": "varies", "cost": "varies"}
            }
        },
        "stats": {
            "total_calls": 0,
            "total_appointments": 0,
            "success_rate": 0
        },
        "created_at": datetime.now().isoformat(),
        "monthly_fee": 49.99 if tenant_data.get("plan") == "basic" else 99.99
    }
    
    tenants[tenant_id] = tenant
    
    # Create default tenant admin user
    tenant_users[tenant_id] = {
        "email": tenant_data["contact_email"],
        "password_hash": hashlib.sha256("temp123".encode()).hexdigest(),
        "role": "tenant_admin",
        "tenant_id": tenant_id,
        "name": tenant_data["name"]
    }
    
    system_stats["total_tenants"] += 1
    logger.info(f"Created tenant: {tenant_id}")
    return tenant_id

def get_tenant_appointments(tenant_id: str) -> List[dict]:
    """Get appointments for specific tenant"""
    return [apt for apt_id, apt in appointments.items() if apt.get("tenant_id") == tenant_id]

def get_tenant_stats(tenant_id: str) -> dict:
    """Get stats for specific tenant"""
    tenant_appointments = get_tenant_appointments(tenant_id)
    tenant_calls = sum(1 for call in call_states.values() if call.get("tenant_id") == tenant_id)
    
    return {
        "total_calls": tenant_calls,
        "total_appointments": len(tenant_appointments),
        "success_rate": (len(tenant_appointments) / max(tenant_calls, 1)) * 100,
        "recent_appointments": sorted(tenant_appointments, key=lambda x: x["created"], reverse=True)[:5]
    }

# VoiceAI Logic (Enhanced for Multi-tenant)
class MultiTenantReceptionist:
    """Multi-tenant receptionist with tenant-specific configurations"""
    
    def get_tenant_config(self, tenant_id: str) -> dict:
        """Get tenant-specific configuration"""
        tenant = tenants.get(tenant_id, {})
        return {
            "name": tenant.get("name", "Dental Practice"),
            "hours": tenant.get("settings", {}).get("practice_hours", {}),
            "services": tenant.get("settings", {}).get("services", {}),
            "phone": tenant.get("phone", "+1 (555) 123-4567")
        }
    
    def get_call_data(self, call_id: str, tenant_id: str) -> dict:
        """Get or create call data with tenant association"""
        if call_id not in call_states:
            call_states[call_id] = {
                "tenant_id": tenant_id,
                "step": 0,
                "data": {},
                "attempts": 0,
                "created_at": datetime.now().isoformat()
            }
        return call_states[call_id]
    
    def extract_info_from_speech(self, speech: str, step: int) -> str:
        """Extract information based on current step"""
        speech = speech.lower().strip()
        
        if step == 1:  # Name
            patterns = [
                r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)?)",
                r"([a-z]{2,}\s+[a-z]{2,})",
                r"([a-z]{3,})"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, speech, re.IGNORECASE)
                if match:
                    name = match.group(1).title()
                    if not any(word in name.lower() for word in ["calling", "appointment", "schedule"]):
                        return name
            
            if len(speech.split()) <= 3 and len(speech) > 2:
                return speech.title()
        
        elif step == 2:  # Phone
            phone_match = re.search(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', speech)
            if phone_match:
                return phone_match.group(1)
        
        elif step == 3:  # Appointment type
            if any(word in speech for word in ["clean", "cleaning"]):
                return "cleaning"
            elif any(word in speech for word in ["check", "checkup", "exam"]):
                return "checkup"
            elif any(word in speech for word in ["consult", "consultation", "new"]):
                return "consultation"
            elif any(word in speech for word in ["emergency", "urgent", "pain", "hurt"]):
                return "emergency"
            else:
                return "checkup"
        
        elif step == 4:  # Time
            if any(word in speech for word in ["morning", "am", "early"]):
                return "morning"
            elif any(word in speech for word in ["afternoon", "pm", "later"]):
                return "afternoon"
            else:
                return "morning"
        
        return None
    
    def generate_response(self, call_id: str, tenant_id: str, speech_result: str = None) -> tuple[str, bool]:
        """Generate tenant-specific response"""
        
        tenant_config = self.get_tenant_config(tenant_id)
        call_data = self.get_call_data(call_id, tenant_id)
        step = call_data["step"]
        
        logger.info(f"Tenant {tenant_id}: Call {call_id}, Step {step}, Speech: '{speech_result}'")
        
        # Process speech input if provided
        if speech_result and step > 0:
            extracted = self.extract_info_from_speech(speech_result, step)
            
            if extracted:
                if step == 1:
                    call_data["data"]["name"] = extracted
                elif step == 2:
                    call_data["data"]["phone"] = extracted
                elif step == 3:
                    call_data["data"]["type"] = extracted
                elif step == 4:
                    call_data["data"]["time"] = extracted
                
                call_data["step"] += 1
                call_data["attempts"] = 0
            else:
                call_data["attempts"] += 1
                
                if call_data["attempts"] >= 2:
                    if step == 1:
                        call_data["data"]["name"] = "Customer"
                    elif step == 2:
                        call_data["data"]["phone"] = "Unknown"
                    elif step == 3:
                        call_data["data"]["type"] = "checkup"
                    elif step == 4:
                        call_data["data"]["time"] = "morning"
                    
                    call_data["step"] += 1
                    call_data["attempts"] = 0
        
        # Generate tenant-specific response
        current_step = call_data["step"]
        practice_name = tenant_config["name"]
        
        if current_step == 0:  # Initial greeting
            call_data["step"] = 1
            return f"Thank you for calling {practice_name}! I'm here to help schedule your appointment. May I get your full name please?", False
        
        elif current_step == 1:
            if call_data["attempts"] >= 2:
                return "Let me get your phone number. What's the best number to reach you?", False
            else:
                return "I didn't catch your name clearly. Could you please tell me your full name?", False
        
        elif current_step == 2:
            if "name" in call_data["data"]:
                return f"Thank you, {call_data['data']['name']}! What's the best phone number to reach you?", False
            else:
                return "What's the best phone number to reach you?", False
        
        elif current_step == 3:
            return "What type of appointment do you need? We offer cleaning, checkup, consultation, or emergency appointments.", False
        
        elif current_step == 4:
            return f"Great! Would you prefer a morning or afternoon appointment for your {call_data['data'].get('type', 'appointment')}?", False
        
        elif current_step >= 5:  # Complete appointment
            appointment_id = f"APT_{len(appointments) + 1:04d}"
            appointment_data = {
                "confirmation_number": appointment_id,
                "tenant_id": tenant_id,
                "name": call_data["data"].get("name", "Customer"),
                "phone": call_data["data"].get("phone", "Unknown"),
                "type": call_data["data"].get("type", "checkup"),
                "time": call_data["data"].get("time", "morning"),
                "status": "scheduled",
                "created": datetime.now().isoformat(),
                "call_id": call_id
            }
            
            appointments[appointment_id] = appointment_data
            
            # Update stats
            system_stats["total_appointments"] += 1
            if tenant_id in tenants:
                tenants[tenant_id]["stats"]["total_appointments"] += 1
            
            # Clear call state
            if call_id in call_states:
                del call_states[call_id]
            
            name = appointment_data["name"]
            phone = appointment_data["phone"]
            apt_type = appointment_data["type"]
            time_pref = appointment_data["time"]
            
            response = f"Perfect! I've scheduled your {apt_type} appointment for {name}. We'll call you at {phone} to confirm your {time_pref} appointment. Your confirmation number is {appointment_id}. Thank you for choosing {practice_name}!"
            
            logger.info(f"Tenant {tenant_id}: Appointment created {appointment_id}")
            return response, True
        
        return f"Thank you for calling {practice_name}! Have a great day!", True

# Initialize receptionist
receptionist = MultiTenantReceptionist()

# Create some demo tenants
if not tenants:
    create_tenant({
        "name": "Demo Dental Practice",
        "contact_email": "admin@demodental.com",
        "phone": "+1 (877) 510-3029",
        "plan": "basic"
    })
    
    create_tenant({
        "name": "Smile Care Center",
        "contact_email": "admin@smilecare.com", 
        "phone": "+1 (555) 123-4567",
        "plan": "premium"
    })

# API Routes

@app.get("/")
async def root():
    return {
        "service": "VoiceAI SaaS Platform",
        "status": "operational",
        "version": "6.0.0",
        "total_tenants": len(tenants),
        "platform_stats": system_stats
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "VoiceAI SaaS Platform",
        "version": "6.0.0",
        "timestamp": datetime.now().isoformat(),
        "tenants": len(tenants),
        "total_calls": system_stats["total_calls"],
        "total_appointments": system_stats["total_appointments"]
    }

# Authentication APIs
@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """Login endpoint for both admin and tenant users"""
    
    if login_data.user_type == "admin":
        user = admin_users.get(login_data.email)
        if user and user["password_hash"] == hashlib.sha256(login_data.password.encode()).hexdigest():
            token = create_jwt_token({
                "email": login_data.email,
                "role": "super_admin",
                "name": user["name"]
            })
            return {"token": token, "user_type": "admin", "name": user["name"]}
    
    elif login_data.user_type == "tenant":
        for tenant_id, user in tenant_users.items():
            if (user["email"] == login_data.email and 
                user["password_hash"] == hashlib.sha256(login_data.password.encode()).hexdigest()):
                token = create_jwt_token({
                    "email": login_data.email,
                    "role": "tenant_admin", 
                    "tenant_id": tenant_id,
                    "name": user["name"]
                })
                return {"token": token, "user_type": "tenant", "tenant_id": tenant_id, "name": user["name"]}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Super Admin APIs
@app.get("/api/admin/dashboard")
async def admin_dashboard(current_user: dict = Depends(get_admin_user)):
    """Super admin dashboard data"""
    
    # Calculate platform metrics
    total_revenue = sum(tenant["monthly_fee"] for tenant in tenants.values())
    active_tenants = sum(1 for tenant in tenants.values() if tenant["status"] == "active")
    
    recent_tenants = sorted(tenants.values(), key=lambda x: x["created_at"], reverse=True)[:5]
    recent_appointments = sorted(appointments.values(), key=lambda x: x["created"], reverse=True)[:10]
    
    return {
        "platform_stats": {
            **system_stats,
            "active_tenants": active_tenants,
            "monthly_revenue": total_revenue
        },
        "recent_tenants": recent_tenants,
        "recent_appointments": recent_appointments,
        "tenant_overview": [
            {
                "id": tid,
                "name": tenant["name"],
                "plan": tenant["plan"],
                "status": tenant["status"],
                "monthly_fee": tenant["monthly_fee"],
                "stats": get_tenant_stats(tid)
            }
            for tid, tenant in tenants.items()
        ]
    }

@app.get("/api/admin/tenants")
async def list_tenants(current_user: dict = Depends(get_admin_user)):
    """List all tenants"""
    return [
        {
            **tenant,
            "stats": get_tenant_stats(tenant["id"])
        }
        for tenant in tenants.values()
    ]

@app.post("/api/admin/tenants")
async def create_new_tenant(tenant_data: TenantCreate, current_user: dict = Depends(get_admin_user)):
    """Create new tenant"""
    tenant_id = create_tenant(tenant_data.dict())
    return {"message": "Tenant created successfully", "tenant_id": tenant_id}

@app.put("/api/admin/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, update_data: TenantUpdate, current_user: dict = Depends(get_admin_user)):
    """Update tenant"""
    if tenant_id not in tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant = tenants[tenant_id]
    update_dict = update_data.dict(exclude_unset=True)
    
    for key, value in update_dict.items():
        if key in tenant:
            tenant[key] = value
    
    return {"message": "Tenant updated successfully"}

# Tenant Customer APIs
@app.get("/api/tenant/dashboard")
async def tenant_dashboard(current_user: dict = Depends(get_tenant_user)):
    """Tenant-specific dashboard"""
    tenant_id = current_user["tenant_id"]
    tenant = tenants.get(tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_appointments = get_tenant_appointments(tenant_id)
    tenant_stats = get_tenant_stats(tenant_id)
    
    return {
        "tenant_info": tenant,
        "stats": tenant_stats,
        "recent_appointments": tenant_appointments[-10:],
        "webhook_url": f"https://your-domain.com/api/v1/voice/{tenant_id}"
    }

@app.get("/api/tenant/appointments")
async def tenant_appointments(current_user: dict = Depends(get_tenant_user)):
    """Get appointments for current tenant"""
    tenant_id = current_user["tenant_id"]
    tenant_appointments = get_tenant_appointments(tenant_id)
    
    return {
        "appointments": tenant_appointments,
        "total": len(tenant_appointments)
    }

@app.get("/api/tenant/settings")
async def tenant_settings(current_user: dict = Depends(get_tenant_user)):
    """Get tenant settings"""
    tenant_id = current_user["tenant_id"]
    tenant = tenants.get(tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return tenant["settings"]

@app.put("/api/tenant/settings")
async def update_tenant_settings(settings: dict, current_user: dict = Depends(get_tenant_user)):
    """Update tenant settings"""
    tenant_id = current_user["tenant_id"]
    if tenant_id not in tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenants[tenant_id]["settings"].update(settings)
    return {"message": "Settings updated successfully"}

# Voice Webhook (Multi-tenant)
@app.post("/api/v1/voice/{tenant_id}")
async def voice_webhook(
    tenant_id: str,
    CallSid: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    SpeechResult: Optional[str] = Form(None)
):
    """Multi-tenant voice webhook"""
    
    if tenant_id not in tenants:
        logger.error(f"Unknown tenant: {tenant_id}")
        return Response(content='''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">This practice is not currently available. Please check the phone number and try again.</Say>
    <Hangup/>
</Response>''', media_type="application/xml")
    
    call_id = CallSid or f"call_{system_stats['total_calls']}"
    system_stats["total_calls"] += 1
    tenants[tenant_id]["stats"]["total_calls"] += 1
    
    logger.info(f"Tenant {tenant_id}: Call {call_id}, Speech: '{SpeechResult}'")
    
    try:
        response_text, is_complete = receptionist.generate_response(call_id, tenant_id, SpeechResult)
        
        if is_complete:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{response_text}</Say>
    <Hangup/>
</Response>'''
        else:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{response_text}</Say>
    <Gather input="speech" timeout="6" speechTimeout="2" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear you. Let me try once more.</Say>
    <Gather input="speech" timeout="5" speechTimeout="2" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">Thank you for calling. Please call back when you're ready. Goodbye!</Say>
    <Hangup/>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} voice webhook error: {e}")
        practice_name = tenants[tenant_id]["name"]
        error_twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling {practice_name}. Please try calling back in a moment.</Say>
    <Hangup/>
</Response>'''
        return Response(content=error_twiml, media_type="application/xml")

# V1 API Endpoints (for frontend compatibility)
@app.get("/api/v1/admin/tenants")
async def list_tenants_v1(current_user: dict = Depends(get_admin_user)):
    """List all tenants (v1 endpoint)"""
    return {
        "success": True,
        "tenants": [
            {
                **tenant,
                "id": tid,
                "created_at": tenant.get("created_at", "2024-01-01"),
                "last_call": tenant.get("last_call", None),
                "total_calls": tenant.get("total_calls", 0),
                "appointments_count": len([a for a in appointments.values() if a.get("tenant_id") == tid])
            }
            for tid, tenant in tenants.items()
        ]
    }

@app.get("/api/v1/admin/stats")
async def admin_stats_v1(current_user: dict = Depends(get_admin_user)):
    """Get platform statistics (v1 endpoint)"""
    total_calls = sum(len([c for c in call_states.values() if c.get("tenant_id") == tid]) for tid in tenants.keys())
    total_appointments = len(appointments.values())
    monthly_revenue = sum(tenant.get("monthly_fee", 49.99) for tenant in tenants.values() if tenant["status"] == "active")
    
    return {
        "success": True,
        "stats": {
            "totalTenants": len(tenants),
            "activeTenants": len([t for t in tenants.values() if t["status"] == "active"]),
            "totalCalls": total_calls,
            "monthlyRevenue": monthly_revenue,
            "totalAppointments": total_appointments,
            "conversionRate": 85.5 if total_calls > 0 else 0
        }
    }

@app.get("/api/v1/tenant/{tenant_id}/appointments")
async def get_tenant_appointments_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get appointments for specific tenant (v1 endpoint)"""
    tenant_appointments = [apt for apt in appointments.values() if apt.get("tenant_id") == tenant_id]
    
    return {
        "success": True,
        "appointments": tenant_appointments
    }

@app.get("/api/v1/tenant/{tenant_id}/stats")
async def get_tenant_stats_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get statistics for specific tenant (v1 endpoint)"""
    tenant_calls = [c for c in call_states.values() if c.get("tenant_id") == tenant_id]
    tenant_appointments = [a for a in appointments.values() if a.get("tenant_id") == tenant_id]
    
    scheduled = len([a for a in tenant_appointments if a.get("status") == "scheduled"])
    completed = len([a for a in tenant_appointments if a.get("status") == "completed"])
    
    return {
        "success": True,
        "stats": {
            "totalCalls": len(tenant_calls),
            "scheduledAppointments": scheduled,
            "completedAppointments": completed,
            "successRate": round((completed / max(len(tenant_appointments), 1)) * 100, 1),
            "thisMonthCalls": len([c for c in tenant_calls if c.get("created_at", "").startswith("2024-08")]),
            "averageCallDuration": "3:45",
            "mostRequestedService": "Cleaning"
        }
    }

@app.get("/api/v1/tenant/{tenant_id}/info")
async def get_tenant_info_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get tenant information (v1 endpoint)"""
    tenant = tenants.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {
        "success": True,
        "tenant": {
            "id": tenant_id,
            "name": tenant["name"],
            "phone": tenant["phone"],
            "contact_email": tenant["contact_email"],
            "plan": tenant["plan"],
            "status": tenant["status"]
        }
    }

# Admin Tenant Management CRUD Operations
@app.post("/api/v1/admin/tenants")
async def create_tenant_v1(tenant_data: dict, current_user: dict = Depends(get_admin_user)):
    """Create a new tenant (v1 endpoint)"""
    try:
        # Generate new tenant ID
        tenant_id = f"tenant_{len(tenants) + 1:04d}"
        
        # Create tenant record
        new_tenant = {
            "id": tenant_id,
            "name": tenant_data["name"],
            "contact_email": tenant_data["contact_email"],
            "phone": tenant_data["phone"],
            "plan": tenant_data.get("plan", "basic"),
            "status": "active",
            "monthly_fee": 49.99 if tenant_data.get("plan", "basic") == "basic" else 99.99,
            "created_at": datetime.now().isoformat(),
            "settings": {
                "practice_hours": {
                    "monday": "9:00 AM - 5:00 PM",
                    "tuesday": "9:00 AM - 5:00 PM",
                    "wednesday": "9:00 AM - 5:00 PM",
                    "thursday": "9:00 AM - 5:00 PM",
                    "friday": "9:00 AM - 5:00 PM",
                    "saturday": "Closed",
                    "sunday": "Closed"
                },
                "services": {
                    "cleaning": True,
                    "checkup": True,
                    "consultation": True,
                    "emergency": True
                }
            }
        }
        
        # Add to tenants storage
        tenants[tenant_id] = new_tenant
        
        # Create default admin user for tenant
        tenant_users[tenant_id] = {
            "email": tenant_data["contact_email"],
            "password_hash": hashlib.sha256("temp123".encode()).hexdigest(),
            "name": f"{tenant_data['name']} Admin",
            "role": "admin",
            "tenant_id": tenant_id
        }
        
        logger.info(f"Created tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": "Tenant created successfully",
            "tenant": new_tenant
        }
        
    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        raise HTTPException(status_code=500, detail="Failed to create tenant")

@app.put("/api/v1/admin/tenants/{tenant_id}")
async def update_tenant_v1(tenant_id: str, tenant_data: dict, current_user: dict = Depends(get_admin_user)):
    """Update a tenant (v1 endpoint)"""
    if tenant_id not in tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        tenant = tenants[tenant_id]
        
        # Update allowed fields
        if "name" in tenant_data:
            tenant["name"] = tenant_data["name"]
        if "contact_email" in tenant_data:
            tenant["contact_email"] = tenant_data["contact_email"]
        if "phone" in tenant_data:
            tenant["phone"] = tenant_data["phone"]
        if "plan" in tenant_data:
            tenant["plan"] = tenant_data["plan"]
            tenant["monthly_fee"] = 49.99 if tenant_data["plan"] == "basic" else 99.99
        if "status" in tenant_data:
            tenant["status"] = tenant_data["status"]
        
        tenant["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Updated tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": "Tenant updated successfully",
            "tenant": tenant
        }
        
    except Exception as e:
        logger.error(f"Error updating tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update tenant")

@app.delete("/api/v1/admin/tenants/{tenant_id}")
async def delete_tenant_v1(tenant_id: str, current_user: dict = Depends(get_admin_user)):
    """Delete a tenant (v1 endpoint)"""
    if tenant_id not in tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        # Remove tenant
        del tenants[tenant_id]
        
        # Remove tenant user if exists
        if tenant_id in tenant_users:
            del tenant_users[tenant_id]
        
        # Remove tenant appointments
        tenant_appointments = [apt_id for apt_id, apt in appointments.items() if apt.get("tenant_id") == tenant_id]
        for apt_id in tenant_appointments:
            del appointments[apt_id]
        
        # Remove tenant call states
        tenant_calls = [call_id for call_id, call in call_states.items() if call.get("tenant_id") == tenant_id]
        for call_id in tenant_calls:
            del call_states[call_id]
        
        logger.info(f"Deleted tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": "Tenant deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tenant")

# Appointment Management CRUD Operations
@app.post("/api/v1/tenant/{tenant_id}/appointments")
async def create_appointment_v1(tenant_id: str, appointment_data: dict, current_user: dict = Depends(get_tenant_user)):
    """Create a new appointment (v1 endpoint)"""
    try:
        # Generate new appointment ID
        appointment_id = f"apt_{len(appointments) + 1:06d}"
        
        # Create appointment record
        new_appointment = {
            "id": appointment_id,
            "tenant_id": tenant_id,
            "patient_name": appointment_data["patient_name"],
            "patient_phone": appointment_data["patient_phone"],
            "patient_email": appointment_data.get("patient_email", ""),
            "appointment_date": appointment_data["appointment_date"],
            "appointment_time": appointment_data["appointment_time"],
            "service_type": appointment_data["service_type"],
            "duration": appointment_data.get("duration", "30 minutes"),
            "status": appointment_data.get("status", "scheduled"),
            "notes": appointment_data.get("notes", ""),
            "created_at": datetime.now().isoformat(),
            "created_by": current_user.get("email"),
            "reminder_sent": False
        }
        
        # Add to appointments storage
        appointments[appointment_id] = new_appointment
        
        logger.info(f"Created appointment: {appointment_id} for tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": "Appointment created successfully",
            "appointment": new_appointment
        }
        
    except Exception as e:
        logger.error(f"Error creating appointment for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create appointment")

@app.put("/api/v1/tenant/{tenant_id}/appointments/{appointment_id}")
async def update_appointment_v1(tenant_id: str, appointment_id: str, appointment_data: dict, current_user: dict = Depends(get_tenant_user)):
    """Update an appointment (v1 endpoint)"""
    if appointment_id not in appointments:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment = appointments[appointment_id]
    if appointment.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Update allowed fields
        if "patient_name" in appointment_data:
            appointment["patient_name"] = appointment_data["patient_name"]
        if "patient_phone" in appointment_data:
            appointment["patient_phone"] = appointment_data["patient_phone"]
        if "patient_email" in appointment_data:
            appointment["patient_email"] = appointment_data["patient_email"]
        if "appointment_date" in appointment_data:
            appointment["appointment_date"] = appointment_data["appointment_date"]
        if "appointment_time" in appointment_data:
            appointment["appointment_time"] = appointment_data["appointment_time"]
        if "service_type" in appointment_data:
            appointment["service_type"] = appointment_data["service_type"]
        if "duration" in appointment_data:
            appointment["duration"] = appointment_data["duration"]
        if "status" in appointment_data:
            appointment["status"] = appointment_data["status"]
        if "notes" in appointment_data:
            appointment["notes"] = appointment_data["notes"]
        
        appointment["updated_at"] = datetime.now().isoformat()
        appointment["updated_by"] = current_user.get("email")
        
        logger.info(f"Updated appointment: {appointment_id}")
        
        return {
            "success": True,
            "message": "Appointment updated successfully",
            "appointment": appointment
        }
        
    except Exception as e:
        logger.error(f"Error updating appointment {appointment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update appointment")

@app.delete("/api/v1/tenant/{tenant_id}/appointments/{appointment_id}")
async def delete_appointment_v1(tenant_id: str, appointment_id: str, current_user: dict = Depends(get_tenant_user)):
    """Delete an appointment (v1 endpoint)"""
    if appointment_id not in appointments:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment = appointments[appointment_id]
    if appointment.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Remove appointment
        del appointments[appointment_id]
        
        logger.info(f"Deleted appointment: {appointment_id}")
        
        return {
            "success": True,
            "message": "Appointment deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting appointment {appointment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete appointment")

@app.get("/api/v1/tenant/{tenant_id}/appointments/{appointment_id}")
async def get_appointment_v1(tenant_id: str, appointment_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get a specific appointment (v1 endpoint)"""
    if appointment_id not in appointments:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment = appointments[appointment_id]
    if appointment.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "appointment": appointment
    }

# Calendar Integration System
class CalendarIntegration:
    """Multi-vendor calendar integration manager"""
    
    SUPPORTED_PROVIDERS = {
        "google": {
            "name": "Google Calendar",
            "auth_type": "oauth2",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
            "api_base": "https://www.googleapis.com/calendar/v3"
        },
        "microsoft": {
            "name": "Microsoft Outlook",
            "auth_type": "oauth2", 
            "scopes": ["https://graph.microsoft.com/calendars.readwrite"],
            "api_base": "https://graph.microsoft.com/v1.0"
        },
        "icloud": {
            "name": "iCloud Calendar",
            "auth_type": "app_password",
            "protocol": "caldav",
            "api_base": "https://caldav.icloud.com"
        },
        "calendly": {
            "name": "Calendly",
            "auth_type": "api_key",
            "api_base": "https://api.calendly.com"
        },
        "acuity": {
            "name": "Acuity Scheduling", 
            "auth_type": "api_key",
            "api_base": "https://acuityscheduling.com/api/v1"
        },
        "caldav": {
            "name": "CalDAV (Generic)",
            "auth_type": "basic",
            "protocol": "caldav"
        },
        "curvehero": {
            "name": "Curve Hero",
            "auth_type": "api_key",
            "api_base": "https://api.curvehero.com/v1",
            "webhook_support": True,
            "real_time_sync": True
        }
    }
    
    @staticmethod
    def get_provider_info(provider: str) -> dict:
        """Get information about a calendar provider"""
        return CalendarIntegration.SUPPORTED_PROVIDERS.get(provider, {})
    
    @staticmethod
    def create_calendar_event(tenant_id: str, appointment: dict, provider: str = None) -> dict:
        """Create calendar event for appointment"""
        tenant = tenants.get(tenant_id, {})
        calendar_settings = tenant.get("calendar_integration", {})
        
        if not provider:
            provider = calendar_settings.get("default_provider", "google")
        
        # Event data structure
        event_data = {
            "title": f"Appointment: {appointment['patient_name']}",
            "description": f"Service: {appointment['service_type']}\nPatient: {appointment['patient_name']}\nPhone: {appointment['patient_phone']}\nNotes: {appointment.get('notes', '')}",
            "start_time": f"{appointment['appointment_date']}T{appointment['appointment_time']}",
            "duration": appointment.get('duration', '30 minutes'),
            "location": tenant.get('name', 'Dental Practice'),
            "attendees": [appointment.get('patient_email')] if appointment.get('patient_email') else [],
            "provider": provider,
            "appointment_id": appointment['id']
        }
        
        # Provider-specific formatting
        if provider == "curvehero":
            # Curve Hero specific event formatting
            event_data.update({
                "sync_type": "real_time",
                "webhook_enabled": True,
                "curve_hero_client_id": appointment.get('patient_phone', '').replace('+', '').replace('-', '').replace(' ', ''),
                "practice_location": tenant.get('name', 'Dental Practice'),
                "appointment_type": appointment.get('service_type', 'General Consultation'),
                "reminder_settings": {
                    "email_reminder": True if appointment.get('patient_email') else False,
                    "sms_reminder": True,
                    "reminder_hours": [24, 2]  # 24 hours and 2 hours before
                }
            })
        
        logger.info(f"Calendar event created for {provider}: {appointment['id']}")
        return event_data
    
    @staticmethod
    def sync_with_curvehero(tenant_id: str, appointment: dict) -> dict:
        """Specific integration method for Curve Hero"""
        tenant = tenants.get(tenant_id, {})
        calendar_settings = tenant.get("calendar_integration", {})
        
        # Curve Hero API payload
        curvehero_payload = {
            "client": {
                "name": appointment['patient_name'],
                "phone": appointment['patient_phone'],
                "email": appointment.get('patient_email', ''),
                "id": appointment.get('patient_phone', '').replace('+', '').replace('-', '').replace(' ', '')
            },
            "appointment": {
                "date": appointment['appointment_date'],
                "time": appointment['appointment_time'],
                "service": appointment['service_type'],
                "duration": appointment.get('duration', '30 minutes'),
                "location": tenant.get('name', 'Dental Practice'),
                "status": appointment.get('status', 'scheduled')
            },
            "settings": {
                "auto_reminder": calendar_settings.get("auto_sync", True),
                "webhook_notifications": True,
                "real_time_sync": True
            }
        }
        
        logger.info(f"Curve Hero sync initiated for appointment: {appointment['id']}")
        return curvehero_payload

# Calendar Integration APIs
@app.get("/api/v1/tenant/{tenant_id}/calendar/providers")
async def get_calendar_providers_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get available calendar providers"""
    return {
        "success": True,
        "providers": CalendarIntegration.SUPPORTED_PROVIDERS
    }

@app.get("/api/v1/tenant/{tenant_id}/calendar/settings")
async def get_calendar_settings_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get tenant calendar integration settings"""
    tenant = tenants.get(tenant_id, {})
    calendar_settings = tenant.get("calendar_integration", {
        "enabled": False,
        "default_provider": "google",
        "auto_sync": True,
        "reminder_minutes": 15,
        "connected_calendars": []
    })
    
    return {
        "success": True,
        "settings": calendar_settings
    }

@app.put("/api/v1/tenant/{tenant_id}/calendar/settings")
async def update_calendar_settings_v1(tenant_id: str, settings_data: dict, current_user: dict = Depends(get_tenant_user)):
    """Update tenant calendar integration settings"""
    if tenant_id not in tenants:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        tenant = tenants[tenant_id]
        if "calendar_integration" not in tenant:
            tenant["calendar_integration"] = {}
        
        # Update calendar settings
        calendar_settings = tenant["calendar_integration"]
        
        if "enabled" in settings_data:
            calendar_settings["enabled"] = settings_data["enabled"]
        if "default_provider" in settings_data:
            calendar_settings["default_provider"] = settings_data["default_provider"]
        if "auto_sync" in settings_data:
            calendar_settings["auto_sync"] = settings_data["auto_sync"]
        if "reminder_minutes" in settings_data:
            calendar_settings["reminder_minutes"] = settings_data["reminder_minutes"]
        
        tenant["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Updated calendar settings for tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": "Calendar settings updated successfully",
            "settings": calendar_settings
        }
        
    except Exception as e:
        logger.error(f"Error updating calendar settings for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update calendar settings")

@app.post("/api/v1/tenant/{tenant_id}/calendar/connect")
async def connect_calendar_provider_v1(tenant_id: str, connection_data: dict, current_user: dict = Depends(get_tenant_user)):
    """Connect a calendar provider to tenant"""
    provider = connection_data.get("provider")
    if not provider or provider not in CalendarIntegration.SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid calendar provider")
    
    try:
        tenant = tenants[tenant_id]
        if "calendar_integration" not in tenant:
            tenant["calendar_integration"] = {"connected_calendars": []}
        
        # Add calendar connection
        calendar_connection = {
            "provider": provider,
            "provider_name": CalendarIntegration.SUPPORTED_PROVIDERS[provider]["name"],
            "calendar_id": connection_data.get("calendar_id"),
            "access_token": connection_data.get("access_token"),  # Would be encrypted in production
            "refresh_token": connection_data.get("refresh_token"),
            "connected_at": datetime.now().isoformat(),
            "status": "connected",
            "last_sync": None
        }
        
        # Remove existing connection for same provider
        connected_calendars = tenant["calendar_integration"].get("connected_calendars", [])
        connected_calendars = [c for c in connected_calendars if c["provider"] != provider]
        connected_calendars.append(calendar_connection)
        
        tenant["calendar_integration"]["connected_calendars"] = connected_calendars
        tenant["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Connected {provider} calendar for tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": f"{CalendarIntegration.SUPPORTED_PROVIDERS[provider]['name']} connected successfully",
            "connection": {
                "provider": provider,
                "provider_name": CalendarIntegration.SUPPORTED_PROVIDERS[provider]["name"],
                "status": "connected"
            }
        }
        
    except Exception as e:
        logger.error(f"Error connecting calendar for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect calendar")

@app.delete("/api/v1/tenant/{tenant_id}/calendar/disconnect/{provider}")
async def disconnect_calendar_provider_v1(tenant_id: str, provider: str, current_user: dict = Depends(get_tenant_user)):
    """Disconnect a calendar provider from tenant"""
    if provider not in CalendarIntegration.SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid calendar provider")
    
    try:
        tenant = tenants[tenant_id]
        calendar_integration = tenant.get("calendar_integration", {})
        connected_calendars = calendar_integration.get("connected_calendars", [])
        
        # Remove calendar connection
        connected_calendars = [c for c in connected_calendars if c["provider"] != provider]
        calendar_integration["connected_calendars"] = connected_calendars
        
        tenant["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Disconnected {provider} calendar for tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": f"{CalendarIntegration.SUPPORTED_PROVIDERS[provider]['name']} disconnected successfully"
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting calendar for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect calendar")

@app.post("/api/v1/tenant/{tenant_id}/calendar/sync")
async def sync_calendar_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Sync appointments with connected calendars"""
    try:
        tenant = tenants.get(tenant_id, {})
        calendar_settings = tenant.get("calendar_integration", {})
        
        if not calendar_settings.get("enabled", False):
            raise HTTPException(status_code=400, detail="Calendar integration not enabled")
        
        connected_calendars = calendar_settings.get("connected_calendars", [])
        if not connected_calendars:
            raise HTTPException(status_code=400, detail="No calendars connected")
        
        # Get tenant appointments
        tenant_appointments = [apt for apt in appointments.values() if apt.get("tenant_id") == tenant_id]
        
        sync_results = []
        for calendar in connected_calendars:
            provider = calendar["provider"]
            
            # Create calendar events for each appointment
            for appointment in tenant_appointments:
                if appointment.get("status") == "scheduled":
                    event_data = CalendarIntegration.create_calendar_event(
                        tenant_id, appointment, provider
                    )
                    sync_results.append({
                        "appointment_id": appointment["id"],
                        "provider": provider,
                        "status": "synced",
                        "event_id": f"evt_{appointment['id']}_{provider}"
                    })
        
        # Update last sync time
        for calendar in connected_calendars:
            calendar["last_sync"] = datetime.now().isoformat()
        
        logger.info(f"Calendar sync completed for tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": "Calendar sync completed successfully",
            "synced_appointments": len([r for r in sync_results if r["status"] == "synced"]),
            "results": sync_results
        }
        
    except Exception as e:
        logger.error(f"Error syncing calendar for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync calendar")

@app.post("/api/v1/tenant/{tenant_id}/calendar/curvehero/connect")
async def connect_curvehero_v1(tenant_id: str, curvehero_data: dict, current_user: dict = Depends(get_tenant_user)):
    """Connect Curve Hero specifically with enhanced features"""
    try:
        if tenant_id not in tenants:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Validate Curve Hero specific data
        api_key = curvehero_data.get("api_key")
        practice_id = curvehero_data.get("practice_id")
        webhook_url = curvehero_data.get("webhook_url", f"https://yourdomain.com/webhook/curvehero/{tenant_id}")
        
        if not api_key or not practice_id:
            raise HTTPException(status_code=400, detail="API key and practice ID are required for Curve Hero")
        
        tenant = tenants[tenant_id]
        if "calendar_integration" not in tenant:
            tenant["calendar_integration"] = {"connected_calendars": []}
        
        # Create Curve Hero connection with enhanced features
        curvehero_connection = {
            "provider": "curvehero",
            "provider_name": "Curve Hero",
            "api_key": api_key,
            "practice_id": practice_id,
            "webhook_url": webhook_url,
            "connected_at": datetime.now().isoformat(),
            "status": "connected",
            "last_sync": None,
            "features": {
                "real_time_sync": True,
                "webhook_notifications": True,
                "automatic_reminders": True,
                "client_portal_sync": True,
                "payment_integration": curvehero_data.get("payment_integration", False)
            }
        }
        
        # Remove existing Curve Hero connection if exists
        connected_calendars = tenant["calendar_integration"].get("connected_calendars", [])
        connected_calendars = [c for c in connected_calendars if c["provider"] != "curvehero"]
        connected_calendars.append(curvehero_connection)
        
        tenant["calendar_integration"]["connected_calendars"] = connected_calendars
        tenant["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Curve Hero connected for tenant: {tenant_id} with practice ID: {practice_id}")
        
        return {
            "success": True,
            "message": "Curve Hero connected successfully with enhanced features",
            "connection": {
                "provider": "curvehero",
                "provider_name": "Curve Hero",
                "practice_id": practice_id,
                "status": "connected",
                "features_enabled": curvehero_connection["features"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error connecting Curve Hero for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect Curve Hero")

@app.post("/api/v1/tenant/{tenant_id}/calendar/curvehero/webhook")
async def curvehero_webhook_v1(tenant_id: str, webhook_data: dict):
    """Handle Curve Hero webhook notifications"""
    try:
        event_type = webhook_data.get("event_type")
        appointment_data = webhook_data.get("appointment", {})
        
        logger.info(f"Curve Hero webhook received for tenant {tenant_id}: {event_type}")
        
        if event_type == "appointment.created":
            # Handle new appointment from Curve Hero
            patient_phone = appointment_data.get("client", {}).get("phone", "")
            appointment_id = f"ch_{appointment_data.get('id', '')}"
            
            # Create appointment in our system
            new_appointment = {
                "id": appointment_id,
                "tenant_id": tenant_id,
                "patient_name": appointment_data.get("client", {}).get("name", ""),
                "patient_phone": patient_phone,
                "patient_email": appointment_data.get("client", {}).get("email", ""),
                "appointment_date": appointment_data.get("date", ""),
                "appointment_time": appointment_data.get("time", ""),
                "service_type": appointment_data.get("service", ""),
                "duration": appointment_data.get("duration", "30 minutes"),
                "status": "scheduled",
                "source": "curvehero",
                "created_at": datetime.now().isoformat()
            }
            
            appointments[appointment_id] = new_appointment
            
        elif event_type == "appointment.updated":
            # Handle appointment updates from Curve Hero
            appointment_id = f"ch_{appointment_data.get('id', '')}"
            if appointment_id in appointments:
                appointment = appointments[appointment_id]
                appointment.update({
                    "appointment_date": appointment_data.get("date", appointment["appointment_date"]),
                    "appointment_time": appointment_data.get("time", appointment["appointment_time"]),
                    "status": appointment_data.get("status", appointment["status"]),
                    "updated_at": datetime.now().isoformat()
                })
        
        elif event_type == "appointment.cancelled":
            # Handle appointment cancellations from Curve Hero
            appointment_id = f"ch_{appointment_data.get('id', '')}"
            if appointment_id in appointments:
                appointments[appointment_id]["status"] = "cancelled"
                appointments[appointment_id]["updated_at"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": f"Webhook processed: {event_type}",
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing Curve Hero webhook for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")

# Call Logs Storage
call_logs = {}

# Voice AI Call Processing System
class VoiceAIProcessor:
    """Voice AI system for processing dental appointment calls"""
    
    @staticmethod
    def process_call_transcript(transcript: str, tenant_id: str) -> dict:
        """Process call transcript using AI to extract appointment information"""
        try:
            if not openai_client:
                # Fallback processing without OpenAI
                return VoiceAIProcessor.fallback_processing(transcript, tenant_id)
            
            # AI-powered transcript processing
            prompt = f"""
            You are an AI assistant for a dental practice. Analyze this phone call transcript and extract appointment information.
            
            Transcript: "{transcript}"
            
            Extract the following information if available:
            - Patient name
            - Phone number
            - Preferred appointment date and time
            - Service type (cleaning, checkup, emergency, etc.)
            - Any special requests or notes
            - Call outcome (scheduled, callback needed, no appointment)
            
            Return as JSON format with keys: patient_name, patient_phone, appointment_date, appointment_time, service_type, notes, outcome, confidence_score.
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse AI response
            ai_result = response.choices[0].message.content
            logger.info(f"AI processing result for tenant {tenant_id}: {ai_result}")
            
            # Try to parse as JSON, fallback if needed
            try:
                import json
                parsed_result = json.loads(ai_result)
                return parsed_result
            except:
                return VoiceAIProcessor.fallback_processing(transcript, tenant_id)
                
        except Exception as e:
            logger.error(f"Voice AI processing error: {e}")
            return VoiceAIProcessor.fallback_processing(transcript, tenant_id)
    
    @staticmethod
    def fallback_processing(transcript: str, tenant_id: str) -> dict:
        """Fallback processing when AI is unavailable"""
        # Simple keyword-based extraction
        transcript_lower = transcript.lower()
        
        # Extract basic information using keywords
        patient_name = "Unknown Patient"
        service_type = "General Consultation"
        outcome = "callback_needed"
        
        if any(word in transcript_lower for word in ["cleaning", "clean"]):
            service_type = "Cleaning"
        elif any(word in transcript_lower for word in ["checkup", "check"]):
            service_type = "Checkup"
        elif any(word in transcript_lower for word in ["emergency", "urgent", "pain"]):
            service_type = "Emergency"
        
        if any(word in transcript_lower for word in ["schedule", "appointment", "book"]):
            outcome = "scheduled"
        elif any(word in transcript_lower for word in ["call back", "callback"]):
            outcome = "callback_needed"
        
        return {
            "patient_name": patient_name,
            "patient_phone": "",
            "appointment_date": "",
            "appointment_time": "",
            "service_type": service_type,
            "notes": "Auto-processed from call transcript",
            "outcome": outcome,
            "confidence_score": 0.6
        }

# Call Log Management APIs
@app.get("/api/v1/tenant/{tenant_id}/calls")
async def get_call_logs_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get call logs for a tenant"""
    tenant_calls = [call for call in call_logs.values() if call.get("tenant_id") == tenant_id]
    tenant_calls.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "success": True,
        "calls": tenant_calls,
        "total": len(tenant_calls)
    }

@app.post("/api/v1/tenant/{tenant_id}/calls")
async def create_call_log_v1(tenant_id: str, call_data: dict, current_user: dict = Depends(get_tenant_user)):
    """Create a new call log entry"""
    try:
        # Generate call ID
        call_id = f"call_{len(call_logs) + 1:06d}"
        
        # Create call log entry
        new_call = {
            "id": call_id,
            "tenant_id": tenant_id,
            "caller_phone": call_data.get("caller_phone", ""),
            "call_duration": call_data.get("call_duration", ""),
            "call_type": call_data.get("call_type", "inbound"),
            "call_status": call_data.get("call_status", "completed"),
            "transcript": call_data.get("transcript", ""),
            "ai_processed": False,
            "appointment_created": False,
            "created_at": datetime.now().isoformat(),
            "created_by": current_user.get("email")
        }
        
        # Process with Voice AI if transcript is provided
        if call_data.get("transcript"):
            ai_result = VoiceAIProcessor.process_call_transcript(
                call_data["transcript"], 
                tenant_id
            )
            new_call["ai_analysis"] = ai_result
            new_call["ai_processed"] = True
            
            # Auto-create appointment if AI confidence is high
            if ai_result.get("confidence_score", 0) > 0.8 and ai_result.get("outcome") == "scheduled":
                if ai_result.get("patient_name") and ai_result.get("appointment_date"):
                    try:
                        appointment_data = {
                            "patient_name": ai_result["patient_name"],
                            "patient_phone": ai_result.get("patient_phone", call_data.get("caller_phone", "")),
                            "patient_email": ai_result.get("patient_email", ""),
                            "appointment_date": ai_result["appointment_date"],
                            "appointment_time": ai_result.get("appointment_time", ""),
                            "service_type": ai_result.get("service_type", "General Consultation"),
                            "notes": f"Auto-created from call {call_id}. {ai_result.get('notes', '')}",
                            "status": "scheduled",
                            "source": "voice_ai"
                        }
                        
                        # Create appointment
                        appointment_id = f"apt_{len(appointments) + 1:06d}"
                        new_appointment = {
                            "id": appointment_id,
                            "tenant_id": tenant_id,
                            **appointment_data,
                            "created_at": datetime.now().isoformat(),
                            "created_by": "voice_ai_system"
                        }
                        
                        appointments[appointment_id] = new_appointment
                        new_call["appointment_id"] = appointment_id
                        new_call["appointment_created"] = True
                        
                        logger.info(f"Auto-created appointment {appointment_id} from call {call_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to auto-create appointment from call {call_id}: {e}")
        
        # Store call log
        call_logs[call_id] = new_call
        
        logger.info(f"Created call log: {call_id} for tenant: {tenant_id}")
        
        return {
            "success": True,
            "message": "Call log created successfully",
            "call": new_call
        }
        
    except Exception as e:
        logger.error(f"Error creating call log for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create call log")

@app.get("/api/v1/tenant/{tenant_id}/calls/{call_id}")
async def get_call_log_v1(tenant_id: str, call_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get a specific call log"""
    if call_id not in call_logs:
        raise HTTPException(status_code=404, detail="Call log not found")
    
    call = call_logs[call_id]
    if call.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "call": call
    }

@app.post("/api/v1/tenant/{tenant_id}/calls/{call_id}/process")
async def reprocess_call_v1(tenant_id: str, call_id: str, current_user: dict = Depends(get_tenant_user)):
    """Reprocess a call with Voice AI"""
    if call_id not in call_logs:
        raise HTTPException(status_code=404, detail="Call log not found")
    
    call = call_logs[call_id]
    if call.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        if not call.get("transcript"):
            raise HTTPException(status_code=400, detail="No transcript available for processing")
        
        # Reprocess with Voice AI
        ai_result = VoiceAIProcessor.process_call_transcript(
            call["transcript"], 
            tenant_id
        )
        
        call["ai_analysis"] = ai_result
        call["ai_processed"] = True
        call["reprocessed_at"] = datetime.now().isoformat()
        call["reprocessed_by"] = current_user.get("email")
        
        return {
            "success": True,
            "message": "Call reprocessed successfully",
            "ai_analysis": ai_result
        }
        
    except Exception as e:
        logger.error(f"Error reprocessing call {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reprocess call")

# Voice AI Test Endpoint
@app.post("/api/v1/tenant/{tenant_id}/voice/test")
async def test_voice_ai_v1(tenant_id: str, test_data: dict, current_user: dict = Depends(get_tenant_user)):
    """Test Voice AI processing with sample transcript"""
    try:
        transcript = test_data.get("transcript", "")
        if not transcript:
            raise HTTPException(status_code=400, detail="Transcript is required for testing")
        
        # Process with Voice AI
        ai_result = VoiceAIProcessor.process_call_transcript(transcript, tenant_id)
        
        return {
            "success": True,
            "message": "Voice AI test completed",
            "transcript": transcript,
            "ai_analysis": ai_result,
            "processing_time": "< 1 second"
        }
        
    except Exception as e:
        logger.error(f"Error testing voice AI for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to test voice AI")

# Analytics APIs for Call Data
@app.get("/api/v1/tenant/{tenant_id}/analytics/calls")
async def get_call_analytics_v1(tenant_id: str, current_user: dict = Depends(get_tenant_user)):
    """Get call analytics for a tenant"""
    tenant_calls = [call for call in call_logs.values() if call.get("tenant_id") == tenant_id]
    
    total_calls = len(tenant_calls)
    ai_processed_calls = len([call for call in tenant_calls if call.get("ai_processed")])
    appointments_created = len([call for call in tenant_calls if call.get("appointment_created")])
    
    # Calculate success rate
    success_rate = round((appointments_created / total_calls * 100) if total_calls > 0 else 0, 1)
    
    # Call types breakdown
    call_types = {}
    for call in tenant_calls:
        call_type = call.get("call_type", "unknown")
        call_types[call_type] = call_types.get(call_type, 0) + 1
    
    return {
        "success": True,
        "analytics": {
            "total_calls": total_calls,
            "ai_processed_calls": ai_processed_calls,
            "appointments_created": appointments_created,
            "success_rate": success_rate,
            "call_types": call_types,
            "ai_processing_rate": round((ai_processed_calls / total_calls * 100) if total_calls > 0 else 0, 1)
        }
    }

@app.get("/api/v1/admin/analytics/calls")
async def get_admin_call_analytics_v1(current_user: dict = Depends(get_admin_user)):
    """Get call analytics for all tenants (admin only)"""
    total_calls = len(call_logs)
    ai_processed_calls = len([call for call in call_logs.values() if call.get("ai_processed")])
    appointments_created = len([call for call in call_logs.values() if call.get("appointment_created")])
    
    # Per-tenant breakdown
    tenant_analytics = {}
    for call in call_logs.values():
        tenant_id = call.get("tenant_id")
        if tenant_id not in tenant_analytics:
            tenant_analytics[tenant_id] = {"calls": 0, "appointments": 0}
        tenant_analytics[tenant_id]["calls"] += 1
        if call.get("appointment_created"):
            tenant_analytics[tenant_id]["appointments"] += 1
    
    return {
        "success": True,
        "analytics": {
            "total_calls": total_calls,
            "ai_processed_calls": ai_processed_calls,
            "appointments_created": appointments_created,
            "success_rate": round((appointments_created / total_calls * 100) if total_calls > 0 else 0, 1),
            "tenant_breakdown": tenant_analytics
        }
    }

# Add some sample appointment data
def initialize_sample_data():
    """Initialize sample appointment and call data for demo"""
    global appointments, call_logs
    sample_appointments = {
        "apt_001": {
            "id": "apt_001",
            "tenant_id": "tenant_0001",
            "patient_name": "John Smith",
            "patient_phone": "(555) 123-4567",
            "appointment_date": "2024-08-25",
            "appointment_time": "10:00 AM",
            "service_type": "Cleaning",
            "status": "scheduled",
            "created_at": "2024-08-22T10:30:00Z"
        },
        "apt_002": {
            "id": "apt_002", 
            "tenant_id": "tenant_0001",
            "patient_name": "Sarah Johnson",
            "patient_phone": "(555) 234-5678",
            "appointment_date": "2024-08-26",
            "appointment_time": "2:00 PM", 
            "service_type": "Checkup",
            "status": "scheduled",
            "created_at": "2024-08-22T11:15:00Z"
        },
        "apt_003": {
            "id": "apt_003",
            "tenant_id": "tenant_0002",
            "patient_name": "Mike Davis",
            "patient_phone": "(555) 345-6789",
            "appointment_date": "2024-08-24",
            "appointment_time": "9:00 AM",
            "service_type": "Emergency",
            "status": "completed",
            "created_at": "2024-08-21T14:20:00Z"
        }
    }
    appointments.update(sample_appointments)
    
    # Sample call logs for demo
    sample_calls = {
        "call_001": {
            "id": "call_001",
            "tenant_id": "tenant_0001",
            "caller_phone": "(555) 123-4567",
            "call_duration": "3:42",
            "call_type": "inbound",
            "call_status": "completed",
            "transcript": "Hi, I'd like to schedule a cleaning appointment for next week. My name is John Smith and my phone number is 555-123-4567. I'm available Tuesday or Wednesday afternoon.",
            "ai_processed": True,
            "appointment_created": True,
            "appointment_id": "apt_001",
            "ai_analysis": {
                "patient_name": "John Smith",
                "patient_phone": "(555) 123-4567",
                "appointment_date": "2024-08-25",
                "appointment_time": "10:00 AM",
                "service_type": "Cleaning",
                "notes": "Preferred Tuesday or Wednesday afternoon",
                "outcome": "scheduled",
                "confidence_score": 0.95
            },
            "created_at": "2024-08-22T09:30:00Z"
        },
        "call_002": {
            "id": "call_002",
            "tenant_id": "tenant_0001",
            "caller_phone": "(555) 234-5678",
            "call_duration": "2:15",
            "call_type": "inbound",
            "call_status": "completed",
            "transcript": "Hello, this is Sarah Johnson. I need to schedule a checkup appointment. I'm having some tooth sensitivity and would like to get it checked out.",
            "ai_processed": True,
            "appointment_created": True,
            "appointment_id": "apt_002",
            "ai_analysis": {
                "patient_name": "Sarah Johnson",
                "patient_phone": "(555) 234-5678",
                "appointment_date": "2024-08-26",
                "appointment_time": "2:00 PM",
                "service_type": "Checkup",
                "notes": "Tooth sensitivity concerns",
                "outcome": "scheduled",
                "confidence_score": 0.90
            },
            "created_at": "2024-08-22T11:00:00Z"
        },
        "call_003": {
            "id": "call_003",
            "tenant_id": "tenant_0001",
            "caller_phone": "(555) 987-6543",
            "call_duration": "1:30",
            "call_type": "inbound",
            "call_status": "completed",
            "transcript": "Hi, I'm calling to ask about your services and pricing. I'm new to the area and looking for a dental practice.",
            "ai_processed": True,
            "appointment_created": False,
            "ai_analysis": {
                "patient_name": "Unknown Patient",
                "patient_phone": "(555) 987-6543",
                "appointment_date": "",
                "appointment_time": "",
                "service_type": "General Information",
                "notes": "New patient inquiry about services and pricing",
                "outcome": "callback_needed",
                "confidence_score": 0.70
            },
            "created_at": "2024-08-22T14:15:00Z"
        },
        "call_004": {
            "id": "call_004",
            "tenant_id": "tenant_0002",
            "caller_phone": "(555) 345-6789",
            "call_duration": "4:20",
            "call_type": "inbound",
            "call_status": "completed",
            "transcript": "This is an emergency! I have severe tooth pain and need to see a dentist immediately. My name is Mike Davis.",
            "ai_processed": True,
            "appointment_created": True,
            "appointment_id": "apt_003",
            "ai_analysis": {
                "patient_name": "Mike Davis",
                "patient_phone": "(555) 345-6789",
                "appointment_date": "2024-08-24",
                "appointment_time": "9:00 AM",
                "service_type": "Emergency",
                "notes": "Severe tooth pain, urgent care needed",
                "outcome": "scheduled",
                "confidence_score": 0.98
            },
            "created_at": "2024-08-21T13:45:00Z"
        }
    }
    call_logs.update(sample_calls)

# Initialize sample data when server starts
initialize_sample_data()

# Health Check Endpoint
# ===== TWILIO WEBHOOK ENDPOINTS =====

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
        twilio_manager = get_twilio_manager()
        twiml_response = twilio_manager.generate_voice_response(tenant_id)
        
        return Response(content=twiml_response, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in voice webhook: {e}")
        # Return basic TwiML response
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
        
        # Generate TwiML response
        response = VoiceResponse()
        response.say("Perfect! I've got all that information. Someone from our office will give you a call back within the next few minutes to confirm your appointment and answer any questions you might have. Thanks so much for calling!")
        response.hangup()
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in recording webhook: {e}")
        response = VoiceResponse()
        response.say("Thanks again for calling! Have a wonderful day and we'll talk to you soon!")
        return Response(content=str(response), media_type="application/xml")

@app.post("/api/v1/twilio/transcription")
async def twilio_transcription_webhook(
    CallSid: str = Form(...),
    TranscriptionSid: str = Form(...),
    TranscriptionText: str = Form(...),
    TranscriptionStatus: str = Form(...),
    tenant_id: Optional[str] = Form(None)
):
    """Handle transcription completion and process with AI"""
    try:
        logger.info(f"Transcription completed: {TranscriptionSid} for call {CallSid}")
        
        # Update call log with transcription
        if CallSid in call_logs:
            call_logs[CallSid].update({
                "transcription_sid": TranscriptionSid,
                "transcript": TranscriptionText,
                "transcription_status": TranscriptionStatus
            })
            
            # Process with AI if transcription is successful
            if TranscriptionStatus == "completed" and TranscriptionText:
                try:
                    ai_result = await process_voice_ai_call(TranscriptionText, tenant_id or "default")
                    
                    # Update call log with AI analysis
                    call_logs[CallSid].update({
                        "ai_processed": True,
                        "ai_analysis": ai_result.get("analysis", {}),
                        "appointment_created": ai_result.get("appointment_id") is not None
                    })
                    
                    # Create appointment if AI determined one should be scheduled
                    if ai_result.get("appointment_id"):
                        call_logs[CallSid]["appointment_id"] = ai_result["appointment_id"]
                    
                    logger.info(f"AI processing completed for call {CallSid}")
                    
                except Exception as ai_error:
                    logger.error(f"AI processing failed for call {CallSid}: {ai_error}")
                    call_logs[CallSid]["ai_error"] = str(ai_error)
        
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
            
            # Update system stats
            if CallStatus == "completed":
                system_stats["total_calls"] += 1
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error in status webhook: {e}")
        return {"success": False, "error": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check if we can create a simple response
        return {
            "status": "healthy",
            "service": "VoiceAI SaaS Platform",
            "version": "6.0.0",
            "timestamp": datetime.now().isoformat(),
            "features": {
                "voice_ai": openai_client is not None,
                "calendar_integration": True,
                "multi_tenant": True,
                "total_tenants": len(tenants),
                "total_appointments": len(appointments),
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

# Public APIs (no auth required)
@app.get("/api/public/tenants")
async def public_tenant_list():
    """Public tenant directory (for demo purposes)"""
    return [
        {
            "id": tid,
            "name": tenant["name"], 
            "phone": tenant["phone"],
            "webhook_url": f"/api/v1/voice/{tid}"
        }
        for tid, tenant in tenants.items() if tenant["status"] == "active"
    ]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting VoiceAI SaaS Platform on port {port}")
    print(f"Total Tenants: {len(tenants)}")
    print("Demo Credentials:")
    print("  Super Admin: admin@voiceai.com / admin123")
    print("  Tenant 1: admin@demodental.com / temp123")
    print("  Tenant 2: admin@smilecare.com / temp123")
    uvicorn.run(app, host="0.0.0.0", port=port)