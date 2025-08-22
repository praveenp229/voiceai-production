"""
VoiceAI 2.0 - Fixed Production Application
Improved conversation flow and speech recognition handling
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
        self.version = "2.0.1"
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
    allow_origins=["*"],
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
    """Improved VoiceAI system with better conversation flow"""
    
    def __init__(self):
        self.system_prompt = """You are a professional dental assistant AI for Demo Dental Practice. 

Your role is to help patients schedule appointments efficiently and professionally.

GUIDELINES:
- Keep responses under 25 words for phone clarity
- Be warm, professional, and helpful
- Ask for one piece of information at a time
- Always advance the conversation forward

APPOINTMENT FLOW:
1. Greet and ask how you can help
2. If they want appointment, ask for name
3. Ask for phone number
4. Ask for appointment type
5. Ask for preferred time
6. Confirm and provide confirmation number

Always move to the next step after getting information."""

    def get_conversation_step(self, call_id: str) -> str:
        """Get current conversation step"""
        history = call_states.get(call_id, [])
        
        # Count how many pieces of info we have
        patient_info = self.extract_patient_info(history)
        
        if not any("appointment" in msg.get("content", "").lower() for msg in history):
            return "greeting"
        elif not patient_info["name"]:
            return "name"
        elif not patient_info["phone"]:
            return "phone"
        elif not patient_info["appointment_type"]:
            return "type"
        elif not patient_info["preferred_time"]:
            return "time"
        else:
            return "confirm"

    def extract_patient_info(self, conversation_history: list) -> Dict[str, Any]:
        """Extract patient information from conversation"""
        info = {
            "name": None,
            "phone": None,
            "appointment_type": None,
            "preferred_time": None
        }
        
        # Combine all user messages
        full_text = " ".join([
            msg.get("content", "") for msg in conversation_history 
            if msg.get("role") == "user"
        ]).lower()
        
        # Extract name - look for common patterns
        name_patterns = [
            r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)?)",
            r"([a-z]{2,}\s+[a-z]{2,})",  # Two words that could be names
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                name_candidate = match.group(1).title()
                # Filter out common phrases
                excluded_words = ["calling", "speaking", "appointment", "dental", "schedule", "like", "want", "need"]
                if not any(word.lower() in name_candidate.lower() for word in excluded_words):
                    info["name"] = name_candidate
                    break
        
        # Extract phone number
        phone_patterns = [
            r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
            r"(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})"
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, full_text)
            if match:
                info["phone"] = match.group(1)
                break
        
        # Extract appointment type
        if any(word in full_text for word in ["cleaning", "clean"]):
            info["appointment_type"] = "cleaning"
        elif any(word in full_text for word in ["checkup", "check", "exam"]):
            info["appointment_type"] = "checkup"
        elif any(word in full_text for word in ["consultation", "consult"]):
            info["appointment_type"] = "consultation"
        elif any(word in full_text for word in ["emergency", "urgent", "pain"]):
            info["appointment_type"] = "emergency"
        
        # Extract time preferences
        if any(word in full_text for word in ["morning", "am"]):
            info["preferred_time"] = "morning"
        elif any(word in full_text for word in ["afternoon", "pm"]):
            info["preferred_time"] = "afternoon"
        
        return info

    async def generate_response(self, user_input: str, call_id: str) -> str:
        """Generate response based on conversation step"""
        
        # Add user input to conversation
        if call_id not in call_states:
            call_states[call_id] = []
        
        call_states[call_id].append({"role": "user", "content": user_input})
        
        # Get current conversation step
        step = self.get_conversation_step(call_id)
        patient_info = self.extract_patient_info(call_states[call_id])
        
        logger.info(f"Call {call_id}: Step={step}, Info={patient_info}")
        
        # Generate response based on step
        if step == "greeting":
            response = "I'd be happy to help you schedule an appointment! May I get your full name please?"
        
        elif step == "name":
            if patient_info["name"]:
                response = f"Thank you, {patient_info['name']}! What's the best phone number to reach you?"
            else:
                response = "I didn't catch your name clearly. Could you please tell me your full name?"
        
        elif step == "phone":
            if patient_info["phone"]:
                response = "Perfect! What type of appointment do you need? We offer cleaning, checkup, consultation, or emergency appointments."
            else:
                response = "Could you please provide your phone number?"
        
        elif step == "type":
            if patient_info["appointment_type"]:
                response = f"Great! For your {patient_info['appointment_type']}, would you prefer morning or afternoon?"
            else:
                response = "What type of appointment would you like? Cleaning, checkup, consultation, or emergency?"
        
        elif step == "time":
            if patient_info["preferred_time"]:
                # Create appointment
                appointment_id = f"APT_{len(appointments) + 1:04d}"
                appointments[appointment_id] = {
                    "name": patient_info["name"],
                    "phone": patient_info["phone"],
                    "type": patient_info["appointment_type"],
                    "time": patient_info["preferred_time"],
                    "created": datetime.now().isoformat()
                }
                system_stats["appointments_created"] += 1
                
                response = f"Perfect! I've scheduled your {patient_info['appointment_type']} appointment for {patient_info['name']}. Your confirmation number is {appointment_id}. We'll call you at {patient_info['phone']} to confirm the exact time. Have a great day!"
            else:
                response = "Would you prefer a morning or afternoon appointment?"
        
        else:
            response = "Thank you for calling Demo Dental Practice. Have a wonderful day!"
        
        # Add AI response to conversation
        call_states[call_id].append({"role": "assistant", "content": response})
        
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
    SpeechResult: Optional[str] = Form(None),
    Digits: Optional[str] = Form(None)
):
    """Voice webhook handler with improved flow"""
    
    call_id = CallSid or f"call_{len(call_states)}"
    
    logger.info(f"Webhook: call={call_id}, status={CallStatus}, speech='{SpeechResult}', digits='{Digits}'")
    system_stats["calls_handled"] += 1
    
    try:
        # Handle initial call
        if CallStatus in ["ringing", "in-progress"] and not SpeechResult and not RecordingUrl:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice! I'm your AI assistant. How can I help you schedule your appointment today?</Say>
    <Gather input="speech" timeout="5" speechTimeout="2" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear anything. Let me try again.</Say>
    <Redirect>/api/v1/voice/{tenant_id}</Redirect>
</Response>'''
        
        # Handle speech input
        elif SpeechResult:
            user_input = SpeechResult.strip()
            logger.info(f"Processing speech: '{user_input}'")
            
            if not user_input or len(user_input) < 2:
                user_input = "I'd like to schedule an appointment"
            
            ai_response = await voice_ai.generate_response(user_input, call_id)
            
            # Check if conversation is complete
            if "confirmation number" in ai_response.lower() or "have a great day" in ai_response.lower():
                twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Hangup/>
</Response>'''
            else:
                twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Gather input="speech" timeout="5" speechTimeout="2" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't catch that. Could you repeat?</Say>
    <Redirect>/api/v1/voice/{tenant_id}</Redirect>
</Response>'''
        
        # Default case
        else:
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Hello! I'm here to help you schedule your dental appointment. Please tell me how I can help you.</Say>
    <Gather input="speech" timeout="5" speechTimeout="2" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Hangup/>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        error_twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">I'm sorry, we're experiencing technical difficulties. Please call back later.</Say>
    <Hangup/>
</Response>'''
        return Response(content=error_twiml, media_type="application/xml")

@app.get("/api/v1/appointments")
async def list_appointments():
    """List all appointments"""
    return {
        "appointments": appointments,
        "total": len(appointments),
        "system_stats": system_stats
    }

@app.get("/api/v1/debug/{call_id}")
async def debug_call(call_id: str):
    """Debug call state"""
    return {
        "call_id": call_id,
        "conversation": call_states.get(call_id, []),
        "step": voice_ai.get_conversation_step(call_id),
        "extracted_info": voice_ai.extract_patient_info(call_states.get(call_id, []))
    }

@app.get("/")
async def root():
    """System overview"""
    return {
        "system": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "description": "Fixed production VoiceAI with improved conversation flow",
        "status": "operational",
        "stats": system_stats,
        "endpoints": {
            "voice_webhook": "/api/v1/voice/{tenant_id}",
            "appointments": "/api/v1/appointments",
            "debug": "/api/v1/debug/{call_id}",
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