"""
VoiceAI 2.0 - Simplified Production Application
Clean, production-ready voice AI system without complex dependencies
"""

import os
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import openai
from typing import Optional, Dict, Any
from datetime import datetime
import re
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
class Settings:
    def __init__(self):
        self.app_name = "VoiceAI 2.0"
        self.version = "2.0.0"
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "150"))
        self.openai_temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        
        # Twilio configuration
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        # Feature flags
        self.enable_conversation_relay = os.getenv("ENABLE_CONVERSATION_RELAY", "false").lower() == "true"
        self.enable_calendar_integration = os.getenv("ENABLE_CALENDAR_INTEGRATION", "false").lower() == "true"
        
        # Performance
        self.max_concurrent_calls = int(os.getenv("MAX_CONCURRENT_CALLS", "100"))
        
    @property
    def is_production(self):
        return self.environment == "production"
    
    @property
    def openai_configured(self):
        return bool(self.openai_api_key)

# Initialize settings
settings = Settings()

# Initialize OpenAI client
client = None
if settings.openai_configured:
    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        logger.info("OpenAI client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Production-ready voice AI system for dental appointment scheduling",
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage (in production, this would be a proper database)
call_states = {}
appointments = {}
system_stats = {
    "calls_handled": 0,
    "appointments_created": 0,
    "start_time": datetime.now().isoformat()
}

class VoiceAI:
    """Simplified VoiceAI system"""
    
    def __init__(self):
        self.system_prompt = """You are a professional dental assistant AI for Demo Dental Practice. 

Your role is to help patients schedule appointments efficiently and professionally.

GUIDELINES:
- Keep responses under 25 words for phone clarity
- Be warm, professional, and helpful
- Ask for one piece of information at a time
- Suggest specific available times when possible

APPOINTMENT FLOW:
1. Greet warmly and ask how you can help
2. Collect: name, phone, appointment type, preferred time
3. Check availability and suggest alternatives if needed
4. Confirm appointment with confirmation number

APPOINTMENT TYPES:
- Cleaning (30 min)
- Checkup (45 min) 
- Consultation (60 min)
- Emergency (immediate)

BUSINESS HOURS:
Monday-Thursday: 9 AM - 5 PM
Friday: 9 AM - 4 PM
Closed weekends

Always end successful bookings with a confirmation number."""

    def extract_patient_info(self, conversation_history: list) -> Dict[str, Any]:
        """Extract patient information from conversation"""
        info = {
            "name": None,
            "phone": None,
            "appointment_type": None,
            "preferred_time": None,
            "urgency": "routine",
            "confidence": 0.0
        }
        
        # Combine all user messages
        full_text = " ".join([
            msg.get("content", "") for msg in conversation_history 
            if msg.get("role") == "user"
        ]).lower()
        
        # Extract name
        name_patterns = [
            r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)*)",
            r"([a-z]+\s+[a-z]+)(?:\s+speaking|$)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                name_candidate = match.group(1).title()
                excluded_words = ["calling", "speaking", "appointment", "dental", "schedule"]
                if not any(word.lower() in name_candidate.lower() for word in excluded_words):
                    info["name"] = name_candidate
                    info["confidence"] += 0.3
                    break
        
        # Extract phone number
        phone_patterns = [
            r"(\d{3}[-.s]?\d{3}[-.s]?\d{4})",
            r"(\(\d{3}\)\s*\d{3}[-.s]?\d{4})"
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, full_text)
            if match:
                info["phone"] = match.group(1)
                info["confidence"] += 0.3
                break
        
        # Extract appointment type
        appointment_keywords = {
            "cleaning": (["cleaning", "clean", "hygiene"], 0.4),
            "checkup": (["checkup", "check", "exam", "examination"], 0.4),
            "consultation": (["consultation", "consult", "new patient"], 0.4),
            "emergency": (["emergency", "urgent", "pain", "hurt"], 0.5)
        }
        
        for apt_type, (keywords, confidence_boost) in appointment_keywords.items():
            if any(keyword in full_text for keyword in keywords):
                info["appointment_type"] = apt_type
                info["confidence"] += confidence_boost
                if apt_type == "emergency":
                    info["urgency"] = "urgent"
                break
        
        # Extract time preferences
        time_keywords = ["morning", "afternoon", "am", "pm"]
        for keyword in time_keywords:
            if keyword in full_text:
                info["preferred_time"] = keyword
                info["confidence"] += 0.2
                break
        
        return info

    async def generate_ai_response(self, user_input: str, call_id: str) -> str:
        """Generate AI response with fallback to rule-based system"""
        
        if client and settings.openai_configured:
            try:
                history = call_states.get(call_id, [])
                
                # Build message context
                messages = [{"role": "system", "content": self.system_prompt}]
                messages.extend(history[-6:])  # Keep recent context
                messages.append({"role": "user", "content": user_input})
                
                # Call OpenAI
                response = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    max_tokens=settings.openai_max_tokens,
                    temperature=settings.openai_temperature
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                # Update conversation history
                if call_id not in call_states:
                    call_states[call_id] = []
                
                call_states[call_id].extend([
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": ai_response}
                ])
                
                logger.info(f"AI response generated for call {call_id}")
                return ai_response
                
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                # Fall back to rule-based system
        
        # Rule-based fallback system
        return await self.generate_rule_based_response(user_input, call_id)

    async def generate_rule_based_response(self, user_input: str, call_id: str) -> str:
        """Rule-based response system as fallback"""
        
        # Get conversation history
        history = call_states.get(call_id, [])
        patient_info = self.extract_patient_info(history + [{"role": "user", "content": user_input}])
        
        conversation_text = " ".join([msg.get("content", "") for msg in history])
        
        # Determine response based on extracted information
        if not history or "appointment" not in conversation_text.lower():
            if "appointment" in user_input.lower() or "schedule" in user_input.lower():
                response = "I'd be happy to help schedule your appointment! May I get your full name?"
            else:
                response = "Hello! I'm here to help with your dental needs. Are you looking to schedule an appointment?"
        
        elif not patient_info["name"]:
            response = "Could you please tell me your full name?"
        
        elif not patient_info["phone"]:
            response = f"Thank you! What's the best phone number to reach you?"
        
        elif not patient_info["appointment_type"]:
            response = "What type of appointment do you need? Cleaning, checkup, consultation, or is this an emergency?"
        
        elif not patient_info["preferred_time"]:
            if patient_info["urgency"] == "urgent":
                response = "For emergencies, I can fit you in today. Do you prefer morning or afternoon?"
            else:
                response = "What time works best for you? Morning or afternoon?"
        
        else:
            # Create appointment
            appointment_id = f"APT_{len(appointments) + 1:04d}"
            appointments[appointment_id] = {
                "name": patient_info["name"],
                "phone": patient_info["phone"],
                "reason": patient_info["appointment_type"] or "checkup",
                "time": patient_info["preferred_time"] or "10:00 AM",
                "urgency": patient_info["urgency"],
                "created_via": "VoiceAI",
                "confidence": patient_info["confidence"]
            }
            system_stats["appointments_created"] += 1
            
            response = f"Perfect! I've scheduled your {patient_info['appointment_type'] or 'appointment'} for {patient_info['name']}. We'll call {patient_info['phone']} to confirm. Your confirmation number is {appointment_id}. Is there anything else I can help you with?"
        
        # Update conversation history
        if call_id not in call_states:
            call_states[call_id] = []
        
        call_states[call_id].extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": response}
        ])
        
        return response

# Initialize the voice AI system
voice_ai = VoiceAI()

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "timestamp": datetime.now().isoformat(),
        "features": {
            "ai_integration": settings.openai_configured,
            "conversation_relay": settings.enable_conversation_relay,
            "production_ready": settings.is_production
        }
    }

@app.post("/api/v1/voice/{tenant_id}")
async def voice_webhook(
    tenant_id: str,
    request: Request,
    From: Optional[str] = Form(None),
    To: Optional[str] = Form(None),
    CallSid: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    RecordingUrl: Optional[str] = Form(None),
    SpeechResult: Optional[str] = Form(None)
):
    """Voice webhook handler"""
    
    call_id = CallSid or f"call_{len(call_states)}"
    host = request.headers.get('host', 'localhost')
    
    logger.info(f"Voice call: tenant={tenant_id}, call={call_id}, status={CallStatus}")
    system_stats["calls_handled"] += 1
    
    try:
        if CallStatus in ["ringing", "in-progress"] and call_id not in call_states:
            # Initial greeting
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice! I'm your AI assistant. How can I help you schedule your appointment today?</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
        
        elif RecordingUrl or SpeechResult:
            # Process recorded speech
            user_input = SpeechResult or "I'd like to schedule an appointment"
            ai_response = await voice_ai.generate_ai_response(user_input, call_id)
            
            # Check if conversation should end
            end_conversation = any(phrase in ai_response.lower() for phrase in [
                "confirmation number", "anything else", "have a great day", "goodbye"
            ])
            
            if end_conversation:
                twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Pause length="1"/>
    <Say voice="Polly.Joanna">Thank you for choosing Demo Dental Practice. Have a wonderful day!</Say>
    <Hangup/>
</Response>'''
            else:
                twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
        
        else:
            # Default greeting
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Hello! You've reached Demo Dental Practice. I'm here to help schedule your appointment. How may I assist you?</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error in voice webhook: {e}")
        error_twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">We're experiencing technical difficulties. Please try again later or call our office directly.</Say>
    <Hangup/>
</Response>'''
        return Response(content=error_twiml, media_type="application/xml")

@app.post("/api/v1/voice/{tenant_id}/process")
async def process_conversation(
    tenant_id: str,
    CallSid: Optional[str] = Form(None),
    RecordingUrl: Optional[str] = Form(None),
    TranscriptionText: Optional[str] = Form(None)
):
    """Process conversation"""
    
    call_id = CallSid or "unknown"
    user_input = TranscriptionText or "I'd like to schedule an appointment"
    
    logger.info(f"Processing conversation: call={call_id}")
    
    try:
        ai_response = await voice_ai.generate_ai_response(user_input, call_id)
        
        # Check if conversation should end
        end_conversation = any(phrase in ai_response.lower() for phrase in [
            "confirmation number", "anything else", "have a great day"
        ])
        
        if end_conversation:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Pause length="1"/>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice. Goodbye!</Say>
    <Hangup/>
</Response>'''
        else:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing conversation: {e}")
        return {"error": "Internal server error"}

@app.get("/api/v1/appointments")
async def list_appointments():
    """List all appointments"""
    return {
        "appointments": appointments,
        "total": len(appointments),
        "system_stats": system_stats
    }

@app.get("/")
async def root():
    """System overview"""
    return {
        "system": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "description": "Production-ready AI voice assistant for dental appointment scheduling",
        "status": "operational",
        "endpoints": {
            "voice_webhook": "/api/v1/voice/{tenant_id}",
            "appointments": "/api/v1/appointments",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print(f"Starting {settings.app_name} v{settings.version}")
    print(f"Environment: {settings.environment}")
    print(f"OpenAI configured: {settings.openai_configured}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        log_level="info" if settings.debug else "warning"
    )