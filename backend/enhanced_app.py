"""
VoiceAI 2.0 - Enhanced Conversation Flow
Complete appointment scheduling with name, phone, type, and time
"""

import os
from fastapi import FastAPI, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import logging
import re

# Simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="VoiceAI Enhanced", version="2.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage
appointments = {}
call_states = {}
system_stats = {
    "calls_handled": 0,
    "appointments_created": 0,
    "start_time": datetime.now().isoformat()
}

class ConversationManager:
    """Manages conversation flow through appointment booking steps"""
    
    def __init__(self):
        self.steps = ["greeting", "name", "phone", "type", "time", "confirm"]
    
    def get_call_state(self, call_id: str) -> dict:
        """Get or create call state"""
        if call_id not in call_states:
            call_states[call_id] = {
                "step": "greeting",
                "data": {},
                "conversation": []
            }
        return call_states[call_id]
    
    def extract_info(self, text: str, step: str) -> str:
        """Extract specific information from speech"""
        text = text.lower().strip()
        
        if step == "name":
            # Look for name patterns
            patterns = [
                r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)?)",
                r"([a-z]{2,}\s+[a-z]{2,})",  # Two words
                r"([a-z]{3,})"  # Single name
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).title()
                    # Filter out common phrases
                    if not any(word in name.lower() for word in ["calling", "speaking", "appointment", "like", "want"]):
                        return name
            return text.title()  # Fallback
        
        elif step == "phone":
            # Extract phone number
            patterns = [
                r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
                r"(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
            
            # If no phone pattern, ask them to repeat
            return None
        
        elif step == "type":
            # Appointment type mapping
            if any(word in text for word in ["cleaning", "clean"]):
                return "cleaning"
            elif any(word in text for word in ["checkup", "check", "exam"]):
                return "checkup"
            elif any(word in text for word in ["consultation", "consult", "new"]):
                return "consultation"
            elif any(word in text for word in ["emergency", "urgent", "pain", "hurt"]):
                return "emergency"
            else:
                return "checkup"  # Default
        
        elif step == "time":
            # Time preference
            if any(word in text for word in ["morning", "am", "early"]):
                return "morning"
            elif any(word in text for word in ["afternoon", "pm", "later"]):
                return "afternoon"
            else:
                return "morning"  # Default
        
        return text

    def generate_response(self, call_id: str, user_input: str = None) -> tuple[str, bool]:
        """Generate TwiML response based on conversation step"""
        state = self.get_call_state(call_id)
        current_step = state["step"]
        
        logger.info(f"Call {call_id}: Step={current_step}, Input='{user_input}'")
        
        # Process user input if provided
        if user_input and current_step != "greeting":
            extracted = self.extract_info(user_input, current_step)
            
            if current_step == "name" and extracted:
                state["data"]["name"] = extracted
                state["step"] = "phone"
            
            elif current_step == "phone":
                if extracted:  # Valid phone number
                    state["data"]["phone"] = extracted
                    state["step"] = "type"
                # If no valid phone, stay on phone step
            
            elif current_step == "type" and extracted:
                state["data"]["type"] = extracted
                state["step"] = "time"
            
            elif current_step == "time" and extracted:
                state["data"]["time"] = extracted
                state["step"] = "confirm"
            
            # Log conversation
            state["conversation"].append({
                "user": user_input,
                "extracted": extracted,
                "step": current_step
            })
        
        # Generate response based on current step
        current_step = state["step"]  # Update after processing
        
        if current_step == "greeting":
            state["step"] = "name"  # Move to next step
            return "Thank you for calling Demo Dental Practice! I'm your AI assistant. To schedule your appointment, may I please get your full name?", False
        
        elif current_step == "name":
            return "I didn't catch your name clearly. Could you please tell me your full name?", False
        
        elif current_step == "phone":
            if "name" in state["data"]:
                return f"Thank you, {state['data']['name']}! What's the best phone number to reach you at?", False
            else:
                return "What's the best phone number to reach you at?", False
        
        elif current_step == "type":
            return "Perfect! What type of appointment do you need today? We offer cleaning, checkup, consultation, or emergency appointments.", False
        
        elif current_step == "time":
            appointment_type = state["data"].get("type", "appointment")
            return f"Great! For your {appointment_type}, would you prefer a morning or afternoon appointment?", False
        
        elif current_step == "confirm":
            # Create appointment
            appointment_id = f"APT_{len(appointments) + 1:04d}"
            appointment_data = {
                "id": appointment_id,
                "name": state["data"].get("name", "Unknown"),
                "phone": state["data"].get("phone", "Unknown"),
                "type": state["data"].get("type", "checkup"),
                "time": state["data"].get("time", "morning"),
                "created": datetime.now().isoformat(),
                "status": "scheduled"
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
            
            return f"Perfect! I've scheduled your {apt_type} appointment for {name}. We'll call you at {phone} to confirm your {time_pref} appointment time. Your confirmation number is {appointment_id}. Thank you for choosing Demo Dental Practice!", True
        
        return "Thank you for calling! Have a great day!", True

# Initialize conversation manager
conversation = ConversationManager()

@app.get("/")
async def root():
    return {
        "service": "VoiceAI Enhanced",
        "status": "operational",
        "version": "2.0.0",
        "stats": system_stats,
        "features": [
            "Complete appointment scheduling",
            "Name and phone collection",
            "Appointment type selection",
            "Time preference handling",
            "Confirmation numbers"
        ]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "VoiceAI Enhanced",
        "version": "2.0.0",
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
    """Enhanced voice webhook with full conversation flow"""
    call_id = CallSid or f"call_{system_stats['calls_handled']}"
    system_stats["calls_handled"] += 1
    
    logger.info(f"Webhook: Call={call_id}, Status={CallStatus}, Speech='{SpeechResult}'")
    
    try:
        # Generate response based on conversation state
        response_text, is_complete = conversation.generate_response(call_id, SpeechResult)
        
        if is_complete:
            # End conversation
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{response_text}</Say>
    <Hangup/>
</Response>'''
        else:
            # Continue conversation
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{response_text}</Say>
    <Gather input="speech" timeout="8" speechTimeout="3" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear you. Let me try again.</Say>
    <Redirect>/api/v1/voice/{tenant_id}</Redirect>
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
async def get_appointments():
    return {
        "appointments": appointments,
        "total": len(appointments),
        "stats": system_stats
    }

@app.get("/api/v1/debug/{call_id}")
async def debug_call(call_id: str):
    """Debug call state for troubleshooting"""
    state = call_states.get(call_id, {})
    return {
        "call_id": call_id,
        "state": state,
        "all_calls": list(call_states.keys())
    }

@app.get("/api/v1/stats")
async def get_stats():
    """System statistics"""
    return {
        "system_stats": system_stats,
        "active_calls": len(call_states),
        "total_appointments": len(appointments),
        "appointment_types": {
            apt["type"]: sum(1 for a in appointments.values() if a["type"] == apt["type"])
            for apt in appointments.values()
        } if appointments else {}
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting Enhanced VoiceAI on port {port}")
    print("Features: Complete appointment scheduling with name, phone, type, and time")
    uvicorn.run(app, host="0.0.0.0", port=port)