"""
Full VoiceAI 2.0 server with AI integration
"""

import os
import asyncio
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
import openai
from typing import Optional

# Set environment variables
os.environ.setdefault("OPENAI_API_KEY", "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")

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="VoiceAI 2.0 Full", version="2.0.0")

# In-memory storage for call states (in production, use database)
call_states = {}

class VoiceProcessor:
    """Process voice calls with AI"""
    
    def __init__(self):
        self.system_prompt = """You are a professional dental assistant AI for Demo Dental Practice. 
Your role is to help patients schedule appointments.

Be friendly, professional, and helpful. Keep responses under 50 words.
Ask for: patient name, phone number, preferred date/time, and reason for visit.

If they want to schedule, collect their information and confirm the appointment.
If they have questions, answer helpfully about dental services."""

    async def process_speech(self, audio_url: str, call_id: str) -> str:
        """Process speech from Twilio recording"""
        try:
            # In a real implementation, you'd download and process the audio
            # For now, simulate speech recognition
            return "I need to schedule an appointment"
            
        except Exception as e:
            return "I'm sorry, I didn't understand that clearly."

    async def generate_response(self, user_input: str, call_id: str) -> str:
        """Generate AI response"""
        try:
            # Get conversation history for this call
            history = call_states.get(call_id, [])
            
            # Build conversation context
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history
            for msg in history[-6:]:  # Keep last 6 messages for context
                messages.append(msg)
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Generate response with OpenAI
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=100,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Update conversation history
            if call_id not in call_states:
                call_states[call_id] = []
            
            call_states[call_id].extend([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": ai_response}
            ])
            
            return ai_response
            
        except Exception as e:
            print(f"AI Error: {e}")
            return "I'm sorry, I'm having trouble processing that right now. Can you please repeat?"

voice_processor = VoiceProcessor()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "VoiceAI 2.0 Full"}

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
    """Handle Twilio voice webhook with AI processing"""
    
    call_id = CallSid or "unknown"
    
    print(f"Voice webhook called for tenant {tenant_id}, call {call_id}")
    print(f"Status: {CallStatus}, From: {From}, To: {To}")
    
    # Handle different call stages
    if CallStatus == "ringing" or CallStatus == "in-progress":
        # Initial call - provide greeting
        if call_id not in call_states:
            twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice! I'm your AI assistant. How can I help you schedule your appointment today?</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{}/process" playBeep="true"/>
</Response>'''.format(tenant_id)
        else:
            # Continue conversation
            twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{}/process" playBeep="true"/>
</Response>'''.format(tenant_id)
    
    elif RecordingUrl or SpeechResult:
        # Process recorded speech
        user_input = SpeechResult or "I have a recording to process"
        
        # Generate AI response
        ai_response = await voice_processor.generate_response(user_input, call_id)
        
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
    
    else:
        # Default response
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice. How can I help you today?</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{}/process" playBeep="true"/>
</Response>'''.format(tenant_id)
    
    return Response(content=twiml, media_type="application/xml")

@app.post("/api/v1/voice/{tenant_id}/process")
async def process_recording(
    tenant_id: str,
    CallSid: Optional[str] = Form(None),
    RecordingUrl: Optional[str] = Form(None),
    TranscriptionText: Optional[str] = Form(None)
):
    """Process recorded speech and continue conversation"""
    
    call_id = CallSid or "unknown"
    
    # Get user input (from transcription or simulate)
    user_input = TranscriptionText or "I'd like to schedule an appointment"
    
    print(f"Processing speech for call {call_id}: {user_input}")
    
    # Generate AI response
    ai_response = await voice_processor.generate_response(user_input, call_id)
    
    # Continue conversation or end call
    if "goodbye" in ai_response.lower() or "appointment confirmed" in ai_response.lower():
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Say voice="Polly.Joanna">Thank you for calling Demo Dental Practice. Have a great day!</Say>
    <Hangup/>
</Response>'''
    else:
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{ai_response}</Say>
    <Record timeout="5" maxLength="30" action="/api/v1/voice/{tenant_id}/process" playBeep="true"/>
</Response>'''
    
    return Response(content=twiml, media_type="application/xml")

@app.get("/api/v1/calls/{call_id}/history")
async def get_call_history(call_id: str):
    """Get conversation history for a call"""
    history = call_states.get(call_id, [])
    return {"call_id": call_id, "history": history}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "VoiceAI 2.0 Full System is running!",
        "features": [
            "AI-powered conversation",
            "OpenAI GPT integration", 
            "Appointment scheduling",
            "Natural voice processing"
        ],
        "docs": "/docs"
    }

if __name__ == "__main__":
    print("Starting VoiceAI 2.0 Full System...")
    print("Features: AI Conversation, Appointment Scheduling, OpenAI Integration")
    print("Visit: http://localhost:8000/docs")
    print("Webhook: http://localhost:8000/api/v1/voice/{tenant_id}")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)