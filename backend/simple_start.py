"""
Simple startup script that bypasses configuration issues
"""

import os
import asyncio
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

# Set environment variables to defaults
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./voiceai.db")
os.environ.setdefault("OPENAI_API_KEY", "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")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACd274a72fbd773fef918d075cca0a6043")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "77a9c40bb46fb965f342c92362aee906")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+18775103029")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")

app = FastAPI(title="VoiceAI 2.0", version="2.0.0")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "VoiceAI 2.0"}

@app.post("/api/v1/voice/{tenant_id}")
async def voice_webhook(tenant_id: str):
    """Simple voice webhook that returns basic TwiML"""
    twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling VoiceAI. We are testing the system. Please hold while we process your request.</Say>
    <Pause length="2"/>
    <Say>This is a test response. Your call is being handled successfully.</Say>
</Response>'''
    return Response(content=twiml, media_type="application/xml")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "VoiceAI 2.0 is running!", "docs": "/docs"}

if __name__ == "__main__":
    print("Starting VoiceAI 2.0 Simple Server...")
    print("Visit: http://localhost:8000/docs")
    print("Webhook: http://localhost:8000/api/v1/voice/{tenant_id}")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)