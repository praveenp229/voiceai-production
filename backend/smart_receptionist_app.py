"""
VoiceAI 2.0 - Smart Receptionist
Intelligent AI that responds naturally to customer questions like a real dental receptionist
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
app = FastAPI(title="Smart Dental Receptionist", version="3.0.0")

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
call_conversations = {}
system_stats = {
    "calls_handled": 0,
    "appointments_created": 0,
    "questions_answered": 0,
    "start_time": datetime.now().isoformat()
}

# Practice Information
PRACTICE_INFO = {
    "name": "Demo Dental Practice",
    "hours": {
        "monday": "9:00 AM - 5:00 PM",
        "tuesday": "9:00 AM - 5:00 PM", 
        "wednesday": "9:00 AM - 5:00 PM",
        "thursday": "9:00 AM - 5:00 PM",
        "friday": "9:00 AM - 4:00 PM",
        "saturday": "Closed",
        "sunday": "Closed"
    },
    "services": {
        "cleaning": {"duration": "30 minutes", "cost": "$120-180"},
        "checkup": {"duration": "45 minutes", "cost": "$150-250"},
        "consultation": {"duration": "60 minutes", "cost": "$100-200"},
        "emergency": {"duration": "varies", "cost": "varies"}
    },
    "insurance": ["Most major insurance plans accepted", "Please call to verify coverage"],
    "location": "123 Dental Street, Demo City, DC 12345",
    "phone": "+1 (877) 510-3029",
    "emergency_policy": "For dental emergencies, we offer same-day appointments when possible"
}

class SmartReceptionist:
    """Intelligent AI receptionist that handles natural conversations"""
    
    def __init__(self):
        self.system_prompt = f"""You are Sarah, a professional and friendly dental receptionist at {PRACTICE_INFO['name']}. 

Your primary goals:
1. Answer customer questions naturally and helpfully
2. Schedule appointments when customers want them
3. Provide accurate practice information
4. Be warm, professional, and efficient

PRACTICE INFORMATION:
- Hours: Mon-Thu 9AM-5PM, Fri 9AM-4PM, Closed weekends
- Services: Cleaning ($120-180, 30 min), Checkup ($150-250, 45 min), Consultation ($100-200, 60 min), Emergency (varies)
- We accept most major insurance plans
- Emergency appointments available same-day when possible
- Location: 123 Dental Street, Demo City, DC 12345

CONVERSATION STYLE:
- Keep responses under 30 words for phone clarity
- Be conversational and natural, not robotic
- Ask follow-up questions when appropriate
- Handle multiple topics in one response
- Guide towards scheduling when appropriate, but don't force it

APPOINTMENT BOOKING:
When customers want to schedule, collect: name, phone, appointment type, time preference
Always provide confirmation numbers for successful bookings.

Common customer questions you should handle naturally:
- Hours and availability
- Costs and insurance
- Service information  
- Emergency situations
- Rescheduling requests
- What to bring/expect

Remember: You're a real person having a conversation, not following a script."""

    def get_conversation_history(self, call_id: str) -> list:
        """Get conversation history for this call"""
        if call_id not in call_conversations:
            call_conversations[call_id] = []
        return call_conversations[call_id]
    
    def add_to_conversation(self, call_id: str, user_input: str, ai_response: str):
        """Add exchange to conversation history"""
        history = self.get_conversation_history(call_id)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": ai_response})
        
        # Keep only last 10 exchanges to manage context length
        if len(history) > 20:
            call_conversations[call_id] = history[-20:]

    def extract_appointment_info(self, conversation: list) -> dict:
        """Extract appointment information from conversation"""
        info = {"name": None, "phone": None, "type": None, "time": None}
        
        # Combine all user messages
        full_text = " ".join([msg["content"] for msg in conversation if msg["role"] == "user"]).lower()
        
        # Extract name
        name_patterns = [
            r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)?)",
            r"([a-z]{2,}\s+[a-z]{2,})"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                name = match.group(1).title()
                if not any(word in name.lower() for word in ["calling", "speaking", "appointment", "like"]):
                    info["name"] = name
                    break
        
        # Extract phone
        phone_patterns = [r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})", r"(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})"]
        for pattern in phone_patterns:
            match = re.search(pattern, full_text)
            if match:
                info["phone"] = match.group(1)
                break
        
        # Extract appointment type
        if any(word in full_text for word in ["cleaning", "clean"]):
            info["type"] = "cleaning"
        elif any(word in full_text for word in ["checkup", "check", "exam"]):
            info["type"] = "checkup"
        elif any(word in full_text for word in ["consultation", "consult", "new patient"]):
            info["type"] = "consultation"
        elif any(word in full_text for word in ["emergency", "urgent", "pain", "hurt"]):
            info["type"] = "emergency"
        
        # Extract time preference
        if any(word in full_text for word in ["morning", "am", "early"]):
            info["time"] = "morning"
        elif any(word in full_text for word in ["afternoon", "pm", "later"]):
            info["time"] = "afternoon"
        
        return info

    def should_complete_appointment(self, info: dict) -> bool:
        """Check if we have enough info to complete appointment booking"""
        return all([info["name"], info["phone"], info["type"], info["time"]])

    async def generate_response(self, call_id: str, user_input: str) -> tuple[str, bool]:
        """Generate natural AI response using OpenAI"""
        
        # Get conversation history
        conversation = self.get_conversation_history(call_id)
        
        # Check if we can complete an appointment booking
        appointment_info = self.extract_appointment_info(conversation + [{"role": "user", "content": user_input}])
        
        if self.should_complete_appointment(appointment_info):
            # Complete the booking
            appointment_id = f"APT_{len(appointments) + 1:04d}"
            appointment_data = {
                "id": appointment_id,
                "name": appointment_info["name"],
                "phone": appointment_info["phone"],
                "type": appointment_info["type"],
                "time": appointment_info["time"],
                "created": datetime.now().isoformat(),
                "status": "scheduled"
            }
            
            appointments[appointment_id] = appointment_data
            system_stats["appointments_created"] += 1
            
            response = f"Perfect! I've scheduled your {appointment_info['type']} appointment for {appointment_info['name']}. We'll call you at {appointment_info['phone']} to confirm your {appointment_info['time']} time slot. Your confirmation number is {appointment_id}. Thank you for choosing {PRACTICE_INFO['name']}!"
            
            self.add_to_conversation(call_id, user_input, response)
            return response, True
        
        # Use OpenAI for natural conversation
        if openai_client:
            try:
                # Build messages for OpenAI
                messages = [{"role": "system", "content": self.system_prompt}]
                
                # Add conversation history
                messages.extend(conversation[-10:])  # Last 10 exchanges
                messages.append({"role": "user", "content": user_input})
                
                # Get AI response
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=100,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content.strip()
                system_stats["questions_answered"] += 1
                
                self.add_to_conversation(call_id, user_input, ai_response)
                return ai_response, False
                
            except Exception as e:
                logger.error(f"OpenAI error: {e}")
        
        # Fallback responses if OpenAI fails
        return self.fallback_response(user_input, appointment_info), False

    def fallback_response(self, user_input: str, appointment_info: dict) -> str:
        """Fallback responses when OpenAI is not available"""
        user_input = user_input.lower()
        
        # Handle common questions
        if any(word in user_input for word in ["hours", "open", "closed"]):
            return f"We're open Monday through Thursday 9 AM to 5 PM, and Friday 9 AM to 4 PM. We're closed weekends. Would you like to schedule an appointment?"
        
        elif any(word in user_input for word in ["cost", "price", "how much"]):
            return "Cleanings are $120-180, checkups $150-250, and consultations $100-200. We accept most insurance. What type of appointment interests you?"
        
        elif any(word in user_input for word in ["insurance", "coverage"]):
            return "We accept most major insurance plans. I can verify your specific coverage when you schedule. Would you like to book an appointment?"
        
        elif any(word in user_input for word in ["emergency", "pain", "urgent", "hurt"]):
            return "For dental emergencies, we offer same-day appointments when possible. Let me get you scheduled right away. What's your name?"
        
        elif any(word in user_input for word in ["schedule", "appointment", "book"]):
            if not appointment_info["name"]:
                return "I'd be happy to schedule your appointment! May I get your full name?"
            elif not appointment_info["phone"]:
                return f"Thank you, {appointment_info['name']}! What's the best phone number to reach you?"
            elif not appointment_info["type"]:
                return "What type of appointment do you need? Cleaning, checkup, consultation, or emergency?"
            elif not appointment_info["time"]:
                return "Would you prefer a morning or afternoon appointment?"
        
        # Default greeting
        return f"Thank you for calling {PRACTICE_INFO['name']}! I'm Sarah, how can I help you today?"

# Initialize receptionist
receptionist = SmartReceptionist()

@app.get("/")
async def root():
    return {
        "service": "Smart Dental Receptionist",
        "status": "operational", 
        "version": "3.0.0",
        "ai_powered": openai_client is not None,
        "stats": system_stats,
        "capabilities": [
            "Natural conversation handling",
            "Practice information Q&A",
            "Intelligent appointment scheduling",
            "Emergency situation handling",
            "Insurance and cost inquiries"
        ]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Smart Dental Receptionist",
        "version": "3.0.0",
        "ai_enabled": openai_client is not None,
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
    """Smart receptionist voice webhook"""
    call_id = CallSid or f"call_{system_stats['calls_handled']}"
    system_stats["calls_handled"] += 1
    
    logger.info(f"Smart Call: {call_id}, Status: {CallStatus}, Speech: '{SpeechResult}'")
    
    try:
        # Handle conversation
        user_input = SpeechResult or "Hello"
        response_text, is_complete = await receptionist.generate_response(call_id, user_input)
        
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
    <Gather input="speech" timeout="10" speechTimeout="3" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear you. Is there anything else I can help you with today?</Say>
    <Gather input="speech" timeout="5" speechTimeout="2" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">Thank you for calling! Have a great day!</Say>
    <Hangup/>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Smart receptionist error: {e}")
        error_twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling {PRACTICE_INFO['name']}. I'm having trouble right now, but please call back and I'll be happy to help you schedule your appointment!</Say>
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

@app.get("/api/v1/practice-info")
async def get_practice_info():
    """Get practice information"""
    return PRACTICE_INFO

@app.get("/api/v1/conversation/{call_id}")
async def get_conversation(call_id: str):
    """Get conversation history for debugging"""
    return {
        "call_id": call_id,
        "conversation": call_conversations.get(call_id, []),
        "appointment_info": receptionist.extract_appointment_info(call_conversations.get(call_id, []))
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting Smart Dental Receptionist on port {port}")
    print(f"AI Powered: {openai_client is not None}")
    print("Capabilities: Natural Q&A, Intelligent scheduling, Practice information")
    uvicorn.run(app, host="0.0.0.0", port=port)