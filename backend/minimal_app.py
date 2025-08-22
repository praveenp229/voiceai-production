"""
VoiceAI 2.0 - Minimal Working Version
Absolutely minimal app that will start and work
"""

import os
from fastapi import FastAPI, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import logging

# Simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="VoiceAI Minimal", version="1.0.0")

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
calls = 0

@app.get("/")
async def root():
    return {
        "service": "VoiceAI Minimal",
        "status": "working",
        "version": "1.0.0",
        "calls": calls,
        "appointments": len(appointments)
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "VoiceAI Minimal",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/voice/{tenant_id}")
async def voice_webhook(
    tenant_id: str,
    CallSid: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    SpeechResult: Optional[str] = Form(None)
):
    """Minimal voice webhook"""
    global calls
    calls += 1
    
    logger.info(f"Call: {CallSid}, Status: {CallStatus}, Speech: {SpeechResult}")
    
    # Simple conversation logic
    if not SpeechResult:
        # Initial greeting
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Hello! Welcome to Demo Dental Practice. Please tell me your name.</Say>
    <Gather input="speech" timeout="5" action="/api/v1/voice/''' + tenant_id + '''">
        <Say></Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear you. Goodbye!</Say>
    <Hangup/>
</Response>'''
    
    else:
        # Got speech input
        name = SpeechResult.strip()
        if name:
            # Create simple appointment
            appointment_id = f"APT_{len(appointments) + 1:03d}"
            appointments[appointment_id] = {
                "name": name,
                "created": datetime.now().isoformat()
            }
            
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you {name}! Your appointment is scheduled. Your confirmation number is {appointment_id}. Goodbye!</Say>
    <Hangup/>
</Response>'''
        else:
            twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">I didn't understand. Please call back. Goodbye!</Say>
    <Hangup/>
</Response>'''
    
    return Response(content=twiml, media_type="application/xml")

@app.get("/api/v1/appointments")
async def get_appointments():
    return {
        "appointments": appointments,
        "total": len(appointments),
        "calls": calls
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting minimal VoiceAI on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)