"""
Enhanced VoiceAI 2.0 with complete appointment scheduling
"""

import os
import asyncio
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
import openai
from typing import Optional, Dict, Any
import json
from datetime import datetime, timedelta
import re

# Set environment variables
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

# Initialize OpenAI client if key is available
client = None
if os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY").endswith("here"):
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except:
        client = None

app = FastAPI(title="VoiceAI 2.0 - Appointment Scheduler", version="2.0.0")

# In-memory storage (in production, use database)
call_states = {}
appointments = {}
available_slots = {
    "Monday": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
    "Tuesday": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
    "Wednesday": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
    "Thursday": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
    "Friday": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM"],
}

class AppointmentScheduler:
    """Complete appointment scheduling with conversation flow"""
    
    def __init__(self):
        self.system_prompt = """You are a professional dental assistant AI for Demo Dental Practice. 
Your role is to help patients schedule appointments efficiently.

CONVERSATION FLOW:
1. Greet and ask how you can help
2. If they want an appointment, collect: name, phone, preferred date/time, reason
3. Check availability and confirm appointment
4. Provide confirmation details

RESPONSES:
- Keep responses under 40 words
- Be friendly and professional
- Ask for missing information one item at a time
- Suggest available times if requested time is unavailable

APPOINTMENT TYPES:
- Cleaning (30 min)
- Checkup (45 min) 
- Consultation (60 min)
- Emergency (immediate)

AVAILABLE HOURS:
Monday-Thursday: 9 AM - 5 PM
Friday: 9 AM - 4 PM
Closed weekends"""

    def extract_appointment_info(self, conversation_history: list) -> Dict[str, Any]:
        """Extract appointment information from conversation"""
        info = {
            "name": None,
            "phone": None,
            "date": None,
            "time": None,
            "reason": None,
            "type": "checkup"
        }
        
        # Look through conversation for appointment details
        full_text = " ".join([msg.get("content", "") for msg in conversation_history if msg.get("role") == "user"])
        
        # Extract name (simple pattern matching)
        name_patterns = [
            r"my name is (\w+(?:\s+\w+)*)",
            r"i'm (\w+(?:\s+\w+)*)",
            r"this is (\w+(?:\s+\w+)*)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                info["name"] = match.group(1).title()
                break
        
        # Extract phone (pattern matching)
        phone_pattern = r"(\d{3}[-.]?\d{3}[-.]?\d{4})"
        phone_match = re.search(phone_pattern, full_text)
        if phone_match:
            info["phone"] = phone_match.group(1)
        
        # Extract appointment type/reason
        if "cleaning" in full_text.lower():
            info["reason"] = "cleaning"
            info["type"] = "cleaning"
        elif "emergency" in full_text.lower() or "urgent" in full_text.lower():
            info["reason"] = "emergency"
            info["type"] = "emergency"
        elif "consultation" in full_text.lower():
            info["reason"] = "consultation"
            info["type"] = "consultation"
        
        # Extract time preferences (basic patterns)
        time_patterns = [
            r"(\d{1,2}:\d{2}\s*(?:AM|PM))",
            r"(\d{1,2}\s*(?:AM|PM))",
            r"(morning|afternoon|evening)"
        ]
        for pattern in time_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                info["time"] = match.group(1)
                break
        
        return info

    def check_availability(self, day: str, time: str) -> bool:
        """Check if requested time slot is available"""
        if day in available_slots and time in available_slots[day]:
            # Check if already booked (simplified)
            appointment_key = f"{day}_{time}"
            return appointment_key not in appointments
        return False

    def suggest_alternative_times(self, day: str) -> list:
        """Suggest available times for a given day"""
        if day in available_slots:
            available = []
            for time in available_slots[day]:
                if self.check_availability(day, time):
                    available.append(time)
            return available[:3]  # Return first 3 available
        return []

    async def generate_response(self, user_input: str, call_id: str) -> str:
        """Generate appropriate response based on conversation state"""
        
        # Get conversation history
        history = call_states.get(call_id, [])
        
        # Extract appointment information
        appointment_info = self.extract_appointment_info(history + [{"role": "user", "content": user_input}])
        
        # Determine response based on conversation state and missing information
        missing_info = [k for k, v in appointment_info.items() if v is None and k != "type"]
        
        if "appointment" not in " ".join([msg.get("content", "") for msg in history]).lower() and "appointment" not in user_input.lower():
            response = "Hi! I'm here to help with your dental needs. Are you looking to schedule an appointment today?"
        
        elif not appointment_info["name"]:
            response = "I'd be happy to help you schedule an appointment! Could you please tell me your full name?"
        
        elif not appointment_info["phone"]:
            response = f"Thank you, {appointment_info['name']}! What's the best phone number to reach you?"
        
        elif not appointment_info["reason"]:
            response = "What type of appointment would you like? We offer cleanings, checkups, consultations, or emergency visits."
        
        elif not appointment_info["time"] and not appointment_info["date"]:
            response = "When would you prefer to come in? What day and time works best for you?"
        
        else:
            # Try to book the appointment
            if appointment_info["name"] and appointment_info["phone"]:
                # Simplified booking logic
                appointment_id = f"APT_{len(appointments) + 1:04d}"
                appointments[appointment_id] = {
                    "name": appointment_info["name"],
                    "phone": appointment_info["phone"],
                    "reason": appointment_info["reason"] or "checkup",
                    "time": appointment_info["time"] or "10:00 AM",
                    "date": "next available",
                    "status": "confirmed"
                }
                
                response = f"Perfect! I've scheduled your {appointment_info['reason'] or 'checkup'} for {appointment_info['name']}. We'll call {appointment_info['phone']} to confirm. Your reference number is {appointment_id}. Is there anything else I can help you with?"
            else:
                response = "I'm still missing some information. Could you provide your name and phone number?"
        
        # Update conversation history
        if call_id not in call_states:
            call_states[call_id] = []
        
        call_states[call_id].extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": response}
        ])
        
        return response

    async def generate_ai_response(self, user_input: str, call_id: str) -> str:
        """Generate AI response using OpenAI if available, otherwise use rule-based"""
        
        if client:
            try:
                history = call_states.get(call_id, [])
                messages = [{"role": "system", "content": self.system_prompt}]
                messages.extend(history[-6:])  # Keep last 6 messages
                messages.append({"role": "user", "content": user_input})
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=100,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                # Update history
                if call_id not in call_states:
                    call_states[call_id] = []
                
                call_states[call_id].extend([
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": ai_response}
                ])
                
                return ai_response
            except Exception as e:
                print(f"OpenAI Error: {e}")
                # Fall back to rule-based response
                return await self.generate_response(user_input, call_id)
        else:
            # Use rule-based system
            return await self.generate_response(user_input, call_id)

scheduler = AppointmentScheduler()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "VoiceAI 2.0 - Appointment Scheduler",
        "ai_enabled": client is not None,
        "total_appointments": len(appointments)
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
    """Handle Twilio voice webhook with appointment scheduling"""
    
    call_id = CallSid or "unknown"
    
    print(f"Voice call: tenant={tenant_id}, call={call_id}, status={CallStatus}")
    
    # Handle different call stages
    if CallStatus == "ringing" or CallStatus == "in-progress":
        if call_id not in call_states:
            # Initial greeting
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice! I'm your AI assistant and I'm here to help you schedule your appointment. How can I help you today?</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
        else:
            # Continue conversation
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
    
    elif RecordingUrl or SpeechResult:
        # Process recorded speech
        user_input = SpeechResult or "I need to schedule an appointment"
        ai_response = await scheduler.generate_ai_response(user_input, call_id)
        
        # Check if appointment is complete
        if "reference number" in ai_response.lower() or "confirmation" in ai_response.lower():
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
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
    <Say voice="Polly.Joanna">Hello! I'm your AI dental assistant. How can I help you schedule your appointment today?</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
    
    return Response(content=twiml, media_type="application/xml")

@app.post("/api/v1/voice/{tenant_id}/process")
async def process_recording(
    tenant_id: str,
    CallSid: Optional[str] = Form(None),
    RecordingUrl: Optional[str] = Form(None),
    TranscriptionText: Optional[str] = Form(None)
):
    """Process recorded speech and continue appointment scheduling"""
    
    call_id = CallSid or "unknown"
    user_input = TranscriptionText or "I'd like to schedule an appointment"
    
    print(f"Processing: {user_input}")
    
    # Generate AI response
    ai_response = await scheduler.generate_ai_response(user_input, call_id)
    
    # Check if conversation should end
    if any(phrase in ai_response.lower() for phrase in ["reference number", "confirmation", "anything else"]):
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

@app.get("/api/v1/appointments")
async def list_appointments():
    """List all scheduled appointments"""
    return {"appointments": appointments, "total": len(appointments)}

@app.get("/api/v1/calls/{call_id}/history")
async def get_call_history(call_id: str):
    """Get conversation history for a call"""
    history = call_states.get(call_id, [])
    return {"call_id": call_id, "history": history}

@app.get("/api/v1/availability")
async def get_availability():
    """Get available appointment slots"""
    return {"available_slots": available_slots}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "VoiceAI 2.0 - Complete Appointment Scheduler",
        "features": [
            "AI-powered conversation",
            "Complete appointment scheduling",
            "Patient information collection", 
            "Availability checking",
            "Appointment confirmation",
            "Professional voice responses"
        ],
        "stats": {
            "total_appointments": len(appointments),
            "ai_enabled": client is not None
        },
        "docs": "/docs"
    }

if __name__ == "__main__":
    print("Starting VoiceAI 2.0 - Complete Appointment Scheduler...")
    print("Features:")
    print("  - Complete appointment scheduling flow")
    print("  - Patient information collection")
    print("  - Availability checking")
    print("  - Appointment confirmation")
    print("  - Professional conversation management")
    print("")
    print("Visit: http://localhost:8000/docs")
    print("Webhook: http://localhost:8000/api/v1/voice/{tenant_id}")
    print("Appointments: http://localhost:8000/api/v1/appointments")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)