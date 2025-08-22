"""
VoiceAI 2.0 - Fixed Flow Version
Simple, reliable conversation flow that won't loop
"""

import os
from fastapi import FastAPI, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import logging
import re
import openai

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

# Create FastAPI app
app = FastAPI(title="VoiceAI Fixed Flow", version="5.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple storage
appointments = {}
call_states = {}
system_stats = {
    "calls_handled": 0,
    "appointments_created": 0,
    "start_time": datetime.now().isoformat()
}

class SimpleReceptionist:
    """Simple, reliable conversation flow"""
    
    def __init__(self):
        self.practice_name = "Demo Dental Practice"

    def get_call_data(self, call_id: str) -> dict:
        """Get or create call data"""
        if call_id not in call_states:
            call_states[call_id] = {
                "step": 0,  # 0=greeting, 1=name, 2=phone, 3=type, 4=time, 5=complete
                "data": {},
                "attempts": 0
            }
        return call_states[call_id]

    def extract_info_from_speech(self, speech: str, step: int) -> str:
        """Extract information based on current step"""
        speech = speech.lower().strip()
        
        if step == 1:  # Name
            # Look for name patterns
            patterns = [
                r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)?)",
                r"([a-z]{2,}\s+[a-z]{2,})",  # Two words
                r"([a-z]{3,})"  # Single name at least 3 chars
            ]
            
            for pattern in patterns:
                match = re.search(pattern, speech, re.IGNORECASE)
                if match:
                    name = match.group(1).title()
                    # Filter common phrases
                    if not any(word in name.lower() for word in ["calling", "appointment", "schedule", "like", "want", "dental"]):
                        return name
            
            # If no pattern match, use the whole speech as name if it's reasonable
            if len(speech.split()) <= 3 and len(speech) > 2:
                return speech.title()
        
        elif step == 2:  # Phone
            # Extract phone number
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
                return "checkup"  # Default
        
        elif step == 4:  # Time
            if any(word in speech for word in ["morning", "am", "early"]):
                return "morning"
            elif any(word in speech for word in ["afternoon", "pm", "later"]):
                return "afternoon"
            else:
                return "morning"  # Default
        
        return None

    def generate_response(self, call_id: str, speech_result: str = None) -> tuple[str, bool]:
        """Generate response based on conversation step"""
        
        call_data = self.get_call_data(call_id)
        step = call_data["step"]
        
        logger.info(f"Call {call_id}: Step {step}, Speech: '{speech_result}'")
        
        # Process speech input if provided
        if speech_result and step > 0:
            extracted = self.extract_info_from_speech(speech_result, step)
            
            if extracted:
                # Save the extracted info
                if step == 1:
                    call_data["data"]["name"] = extracted
                elif step == 2:
                    call_data["data"]["phone"] = extracted
                elif step == 3:
                    call_data["data"]["type"] = extracted
                elif step == 4:
                    call_data["data"]["time"] = extracted
                
                # Move to next step
                call_data["step"] += 1
                call_data["attempts"] = 0
                logger.info(f"Extracted: {extracted}, moving to step {call_data['step']}")
            else:
                # Couldn't extract, increment attempts
                call_data["attempts"] += 1
                logger.info(f"Could not extract info, attempt {call_data['attempts']}")
                
                # If too many attempts, use default or move forward
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
        
        # Generate response based on current step
        current_step = call_data["step"]
        
        if current_step == 0:  # Initial greeting
            call_data["step"] = 1
            return "Thank you for calling Demo Dental Practice! I'm here to help schedule your appointment. May I get your full name please?", False
        
        elif current_step == 1:  # Asking for name
            if call_data["attempts"] >= 2:
                return "Let me get your phone number. What's the best number to reach you?", False
            else:
                return "I didn't catch your name clearly. Could you please tell me your full name?", False
        
        elif current_step == 2:  # Asking for phone
            if "name" in call_data["data"]:
                return f"Thank you, {call_data['data']['name']}! What's the best phone number to reach you?", False
            else:
                return "What's the best phone number to reach you?", False
        
        elif current_step == 3:  # Asking for appointment type
            return "What type of appointment do you need? We offer cleaning, checkup, consultation, or emergency appointments.", False
        
        elif current_step == 4:  # Asking for time
            return f"Great! Would you prefer a morning or afternoon appointment for your {call_data['data'].get('type', 'appointment')}?", False
        
        elif current_step >= 5:  # Complete appointment
            # Create appointment
            appointment_id = f"APT_{len(appointments) + 1:04d}"
            appointment_data = {
                "confirmation_number": appointment_id,
                "name": call_data["data"].get("name", "Customer"),
                "phone": call_data["data"].get("phone", "Unknown"),
                "type": call_data["data"].get("type", "checkup"),
                "time": call_data["data"].get("time", "morning"),
                "created": datetime.now().isoformat()
            }
            
            appointments[appointment_id] = appointment_data
            system_stats["appointments_created"] += 1
            
            # Clear call state
            if call_id in call_states:
                del call_states[call_id]
            
            name = appointment_data["name"]
            phone = appointment_data["phone"]
            apt_type = appointment_data["type"]
            time_pref = appointment_data["time"]
            
            response = f"Perfect! I've scheduled your {apt_type} appointment for {name}. We'll call you at {phone} to confirm your {time_pref} appointment. Your confirmation number is {appointment_id}. Thank you for choosing Demo Dental Practice!"
            
            logger.info(f"Appointment created: {appointment_id}")
            return response, True
        
        # Fallback
        return "Thank you for calling! Have a great day!", True

# Initialize receptionist
receptionist = SimpleReceptionist()

@app.get("/")
async def root():
    return {
        "service": "VoiceAI Fixed Flow",
        "status": "operational",
        "version": "5.0.0",
        "stats": system_stats,
        "active_calls": len(call_states)
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "VoiceAI Fixed Flow",
        "version": "5.0.0",
        "timestamp": datetime.now().isoformat(),
        "stats": system_stats
    }

@app.post("/api/v1/voice/{tenant_id}")
async def voice_webhook(
    tenant_id: str,
    CallSid: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    SpeechResult: Optional[str] = Form(None)
):
    """Simple, reliable voice webhook"""
    call_id = CallSid or f"call_{system_stats['calls_handled']}"
    system_stats["calls_handled"] += 1
    
    logger.info(f"Call: {call_id}, Status: {CallStatus}, Speech: '{SpeechResult}'")
    
    try:
        # Generate response
        response_text, is_complete = receptionist.generate_response(call_id, SpeechResult)
        
        if is_complete:
            # End conversation
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{response_text}</Say>
    <Hangup/>
</Response>'''
        else:
            # Continue conversation with shorter timeout to prevent loops
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
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice. Please call back when you're ready. Goodbye!</Say>
    <Hangup/>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Voice webhook error: {e}")
        error_twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice. Please try calling back in a moment.</Say>
    <Hangup/>
</Response>'''
        return Response(content=error_twiml, media_type="application/xml")

@app.get("/api/v1/appointments")
async def get_appointments():
    return {
        "appointments": appointments,
        "total": len(appointments),
        "stats": system_stats
    }

@app.get("/api/v1/debug/{call_id}")
async def debug_call(call_id: str):
    """Debug specific call"""
    return {
        "call_id": call_id,
        "call_state": call_states.get(call_id, {}),
        "all_active_calls": list(call_states.keys())
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting Fixed Flow VoiceAI on port {port}")
    print("Features: Simple, reliable conversation flow")
    uvicorn.run(app, host="0.0.0.0", port=port)