"""
VoiceAI 2.0 - Database Debug Version
Enhanced logging and fallback to help identify database issues
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

# Configure enhanced logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try database imports with fallback
try:
    from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    import asyncpg
    DATABASE_AVAILABLE = True
    logger.info("Database modules imported successfully")
except ImportError as e:
    logger.error(f"Database import error: {e}")
    DATABASE_AVAILABLE = False

# Initialize OpenAI
openai_client = None
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    try:
        openai_client = openai.OpenAI(api_key=openai_api_key)
        logger.info("OpenAI client initialized")
    except Exception as e:
        logger.error(f"OpenAI initialization failed: {e}")

# Database setup with enhanced debugging
DATABASE_URL = os.getenv("DATABASE_URL")
logger.info(f"DATABASE_URL exists: {bool(DATABASE_URL)}")
logger.info(f"DATABASE_URL type: {DATABASE_URL[:20] if DATABASE_URL else 'None'}...")

engine = None
async_session = None
Base = None

if DATABASE_AVAILABLE and DATABASE_URL:
    try:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
            logger.info("Converted postgres:// to postgresql://")
        
        engine = create_async_engine(DATABASE_URL, echo=True)  # Enable SQL logging
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        logger.info("PostgreSQL async engine created successfully")
        
        # Database models
        Base = declarative_base()
        
        class Appointment(Base):
            __tablename__ = "appointments"
            
            id = Column(Integer, primary_key=True, autoincrement=True)
            confirmation_number = Column(String(20), unique=True, nullable=False)
            customer_name = Column(String(255), nullable=False)
            customer_phone = Column(String(20), nullable=False)
            appointment_type = Column(String(50), nullable=False)
            time_preference = Column(String(20), nullable=False)
            status = Column(String(20), default="scheduled")
            created_at = Column(DateTime, default=datetime.utcnow)
        
        class CallLog(Base):
            __tablename__ = "call_logs"
            
            id = Column(Integer, primary_key=True, autoincrement=True)
            call_sid = Column(String(50), unique=True, nullable=False)
            caller_phone = Column(String(20), nullable=True)
            conversation_summary = Column(Text, nullable=True)
            appointment_created = Column(Boolean, default=False)
            created_at = Column(DateTime, default=datetime.utcnow)
        
        logger.info("Database models defined successfully")
        
    except Exception as e:
        logger.error(f"Database setup error: {e}")
        DATABASE_AVAILABLE = False

# Create FastAPI app
app = FastAPI(title="VoiceAI Debug", version="4.1.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage - both in-memory and database
appointments_memory = {}
call_conversations = {}
system_stats = {
    "calls_handled": 0,
    "appointments_created": 0,
    "appointments_created_memory": 0,
    "database_errors": 0,
    "start_time": datetime.now().isoformat()
}

# Practice Information
PRACTICE_INFO = {
    "name": "Demo Dental Practice",
    "phone": "+1 (877) 510-3029"
}

# Database functions with enhanced error handling
async def create_tables():
    """Create database tables with detailed logging"""
    if not DATABASE_AVAILABLE or not engine:
        logger.warning("Database not available, skipping table creation")
        return False
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully")
        return True
    except Exception as e:
        logger.error(f"Database table creation error: {e}")
        system_stats["database_errors"] += 1
        return False

async def create_appointment_in_db(appointment_data: dict) -> str:
    """Create appointment in database with fallback to memory"""
    confirmation_number = f"APT_{system_stats['appointments_created'] + system_stats['appointments_created_memory'] + 1:04d}"
    
    # Always save to memory as backup
    appointments_memory[confirmation_number] = {
        **appointment_data,
        "confirmation_number": confirmation_number,
        "created_at": datetime.now().isoformat(),
        "stored_in": "memory"
    }
    system_stats["appointments_created_memory"] += 1
    logger.info(f"Appointment saved to memory: {confirmation_number}")
    
    # Try to save to database
    if DATABASE_AVAILABLE and async_session:
        try:
            async with async_session() as session:
                appointment = Appointment(
                    confirmation_number=confirmation_number,
                    customer_name=appointment_data["name"],
                    customer_phone=appointment_data["phone"],
                    appointment_type=appointment_data["type"],
                    time_preference=appointment_data["time"],
                    status="scheduled"
                )
                
                session.add(appointment)
                await session.commit()
                
                # Update memory record
                appointments_memory[confirmation_number]["stored_in"] = "database"
                system_stats["appointments_created"] += 1
                logger.info(f"Appointment saved to database: {confirmation_number}")
                
        except Exception as e:
            logger.error(f"Database save error: {e}")
            system_stats["database_errors"] += 1
            # Keep memory version as fallback
    
    return confirmation_number

async def get_appointments_from_storage():
    """Get appointments from both database and memory"""
    all_appointments = []
    
    # Get from database
    if DATABASE_AVAILABLE and async_session:
        try:
            async with async_session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Appointment).order_by(Appointment.created_at.desc()).limit(50)
                )
                db_appointments = result.scalars().all()
                
                for apt in db_appointments:
                    all_appointments.append({
                        "id": apt.confirmation_number,
                        "name": apt.customer_name,
                        "phone": apt.customer_phone,
                        "type": apt.appointment_type,
                        "time": apt.time_preference,
                        "status": apt.status,
                        "created": apt.created_at.isoformat(),
                        "stored_in": "database"
                    })
                
                logger.info(f"Retrieved {len(db_appointments)} appointments from database")
                
        except Exception as e:
            logger.error(f"Database read error: {e}")
            system_stats["database_errors"] += 1
    
    # Add memory appointments (excluding those already in database)
    for apt_id, apt_data in appointments_memory.items():
        if not any(apt["id"] == apt_id for apt in all_appointments):
            all_appointments.append({
                "id": apt_id,
                "name": apt_data["name"],
                "phone": apt_data["phone"],
                "type": apt_data["type"],
                "time": apt_data["time"],
                "created": apt_data["created_at"],
                "stored_in": apt_data.get("stored_in", "memory_only")
            })
    
    return all_appointments

class SmartReceptionist:
    """Enhanced receptionist with detailed logging"""
    
    def __init__(self):
        self.system_prompt = f"""You are Sarah, a professional and friendly dental receptionist at {PRACTICE_INFO['name']}. 

Your primary goals:
1. Answer customer questions naturally and helpfully
2. Schedule appointments when customers want them
3. Provide accurate practice information
4. Be warm, professional, and efficient

CONVERSATION STYLE:
- Keep responses under 30 words for phone clarity
- Be conversational and natural
- Guide towards scheduling when appropriate

APPOINTMENT BOOKING:
When customers want to schedule, collect: name, phone, appointment type, time preference
Always provide confirmation numbers for successful bookings."""

    def get_conversation_history(self, call_id: str) -> list:
        if call_id not in call_conversations:
            call_conversations[call_id] = []
        return call_conversations[call_id]
    
    def add_to_conversation(self, call_id: str, user_input: str, ai_response: str):
        history = self.get_conversation_history(call_id)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": ai_response})
        
        if len(history) > 20:
            call_conversations[call_id] = history[-20:]

    def extract_appointment_info(self, conversation: list) -> dict:
        """Extract appointment information with detailed logging"""
        info = {"name": None, "phone": None, "type": None, "time": None}
        
        full_text = " ".join([msg["content"] for msg in conversation if msg["role"] == "user"]).lower()
        logger.info(f"Extracting from text: '{full_text[:100]}...'")
        
        # Extract name
        name_patterns = [
            r"(?:my name is|i'm|this is|i am)\s+([a-z]+(?:\s+[a-z]+)?)",
            r"([a-z]{2,}\s+[a-z]{2,})"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                name = match.group(1).title()
                if not any(word in name.lower() for word in ["calling", "speaking", "appointment"]):
                    info["name"] = name
                    logger.info(f"Extracted name: {name}")
                    break
        
        # Extract phone
        phone_patterns = [r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})", r"(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})"]
        for pattern in phone_patterns:
            match = re.search(pattern, full_text)
            if match:
                info["phone"] = match.group(1)
                logger.info(f"Extracted phone: {info['phone']}")
                break
        
        # Extract appointment type
        if any(word in full_text for word in ["cleaning", "clean"]):
            info["type"] = "cleaning"
        elif any(word in full_text for word in ["checkup", "check", "exam"]):
            info["type"] = "checkup"
        elif any(word in full_text for word in ["consultation", "consult"]):
            info["type"] = "consultation"
        elif any(word in full_text for word in ["emergency", "urgent", "pain"]):
            info["type"] = "emergency"
        
        if info["type"]:
            logger.info(f"Extracted type: {info['type']}")
        
        # Extract time preference
        if any(word in full_text for word in ["morning", "am", "early"]):
            info["time"] = "morning"
        elif any(word in full_text for word in ["afternoon", "pm", "later"]):
            info["time"] = "afternoon"
        
        if info["time"]:
            logger.info(f"Extracted time: {info['time']}")
        
        logger.info(f"Final extracted info: {info}")
        return info

    def should_complete_appointment(self, info: dict) -> bool:
        """Check if we have enough info to complete appointment booking"""
        required = ["name", "phone", "type", "time"]
        has_all = all(info.get(field) for field in required)
        logger.info(f"Should complete appointment: {has_all} (has: {[k for k,v in info.items() if v]})")
        return has_all

    async def generate_response(self, call_id: str, user_input: str) -> tuple[str, bool]:
        """Generate response with enhanced logging"""
        
        conversation = self.get_conversation_history(call_id)
        appointment_info = self.extract_appointment_info(conversation + [{"role": "user", "content": user_input}])
        
        if self.should_complete_appointment(appointment_info):
            logger.info("Completing appointment booking...")
            confirmation_number = await create_appointment_in_db(appointment_info)
            
            response = f"Perfect! I've scheduled your {appointment_info['type']} appointment for {appointment_info['name']}. We'll call you at {appointment_info['phone']} to confirm your {appointment_info['time']} time slot. Your confirmation number is {confirmation_number}. Thank you for choosing {PRACTICE_INFO['name']}!"
            
            self.add_to_conversation(call_id, user_input, response)
            logger.info(f"Appointment completed with confirmation: {confirmation_number}")
            return response, True
        
        # Use OpenAI for conversation
        if openai_client:
            try:
                messages = [{"role": "system", "content": self.system_prompt}]
                messages.extend(conversation[-10:])
                messages.append({"role": "user", "content": user_input})
                
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
        
        # Simple fallback
        return f"Thank you for calling {PRACTICE_INFO['name']}! I'm Sarah, how can I help you today?", False

# Initialize receptionist
receptionist = SmartReceptionist()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup with detailed logging"""
    logger.info("Starting VoiceAI Debug application...")
    logger.info(f"Database available: {DATABASE_AVAILABLE}")
    logger.info(f"OpenAI available: {openai_client is not None}")
    
    if DATABASE_AVAILABLE:
        success = await create_tables()
        logger.info(f"Database initialization: {'Success' if success else 'Failed'}")

@app.get("/")
async def root():
    return {
        "service": "VoiceAI Debug",
        "status": "operational", 
        "version": "4.1.0",
        "database": {
            "available": DATABASE_AVAILABLE,
            "url_configured": bool(DATABASE_URL),
            "engine_created": engine is not None,
            "errors": system_stats["database_errors"]
        },
        "ai_powered": openai_client is not None,
        "stats": system_stats
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "VoiceAI Debug",
        "version": "4.1.0",
        "database_status": "connected" if DATABASE_AVAILABLE else "unavailable",
        "ai_enabled": openai_client is not None,
        "timestamp": datetime.now().isoformat(),
        "stats": system_stats
    }

@app.post("/api/v1/voice/{tenant_id}")
async def voice_webhook(
    tenant_id: str,
    CallSid: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    SpeechResult: Optional[str] = Form(None),
    From: Optional[str] = Form(None)
):
    """Enhanced voice webhook with detailed logging"""
    call_id = CallSid or f"call_{system_stats['calls_handled']}"
    system_stats["calls_handled"] += 1
    
    logger.info(f"=== CALL START ===")
    logger.info(f"Call ID: {call_id}")
    logger.info(f"Status: {CallStatus}")
    logger.info(f"Speech: '{SpeechResult}'")
    logger.info(f"From: {From}")
    
    try:
        user_input = SpeechResult or "Hello"
        response_text, is_complete = await receptionist.generate_response(call_id, user_input)
        
        logger.info(f"AI Response: '{response_text}'")
        logger.info(f"Conversation complete: {is_complete}")
        
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
    <Gather input="speech" timeout="10" speechTimeout="3" action="/api/v1/voice/{tenant_id}">
        <Say voice="Polly.Joanna"></Say>
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear you clearly. Is there anything else I can help you with?</Say>
    <Hangup/>
</Response>'''
        
        logger.info(f"=== CALL END ===")
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Voice webhook error: {e}")
        return Response(content='''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Thank you for calling! Please try again later.</Say>
    <Hangup/>
</Response>''', media_type="application/xml")

@app.get("/api/v1/appointments")
async def get_appointments():
    """Get appointments from all storage methods"""
    appointments = await get_appointments_from_storage()
    return {
        "appointments": appointments,
        "total": len(appointments),
        "stats": system_stats,
        "storage_info": {
            "database_available": DATABASE_AVAILABLE,
            "database_errors": system_stats["database_errors"],
            "memory_appointments": len(appointments_memory)
        }
    }

@app.get("/api/v1/debug/system")
async def debug_system():
    """System debug information"""
    return {
        "database": {
            "available": DATABASE_AVAILABLE,
            "url_configured": bool(DATABASE_URL),
            "url_type": DATABASE_URL[:20] if DATABASE_URL else None,
            "engine_created": engine is not None,
            "errors": system_stats["database_errors"]
        },
        "openai": {
            "available": openai_client is not None,
            "key_configured": bool(openai_api_key)
        },
        "stats": system_stats,
        "active_conversations": len(call_conversations),
        "memory_appointments": len(appointments_memory)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting VoiceAI Debug on port {port}")
    print(f"Database: {DATABASE_AVAILABLE}")
    print(f"AI: {openai_client is not None}")
    uvicorn.run(app, host="0.0.0.0", port=port)