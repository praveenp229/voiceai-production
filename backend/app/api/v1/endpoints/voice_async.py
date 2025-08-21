"""
Async voice API endpoints using Celery for background processing
Handles voice calls with queued AI processing to prevent Twilio timeouts
"""

import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.services.tenant_service import TenantService
from app.tasks.voice_tasks import process_voice_async, get_voice_task_status
from app.utils.twilio_utils import validate_twilio_signature, create_twiml_response

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/{tenant_id}/async")
async def handle_voice_call_async(
    tenant_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    From: str = Form(None),
    To: str = Form(None),
    CallSid: str = Form(None),
    CallStatus: str = Form(None),
) -> PlainTextResponse:
    """
    Handle incoming voice calls with async processing
    
    This endpoint immediately returns TwiML while queuing AI processing
    in the background to prevent Twilio webhook timeouts.
    """
    try:
        logger.info(
            "Incoming async voice call",
            tenant_id=tenant_id,
            call_sid=CallSid,
            caller=f"{From[:3]}***" if From else "Unknown"
        )
        
        # Validate Twilio signature
        if not await validate_twilio_signature(request):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Get tenant and validate
        tenant = await TenantService.validate_tenant_access(db, tenant_id=tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Get voice configuration
        voice_config = await TenantService.get_voice_config(db, tenant_id)
        if not voice_config:
            raise HTTPException(status_code=404, detail="Voice configuration not found")
        
        # Return immediate response to prevent timeout
        greeting_text = voice_config.get_greeting_message()
        
        # Create TwiML that will gather input and POST to processing endpoint
        twiml = create_twiml_response(
            message=greeting_text,
            voice=voice_config.voice_name,
            next_action_url=f"/api/v1/voice/{tenant_id}/process-async",
            gather_timeout=10
        )
        
        # Queue background initialization
        background_tasks.add_task(
            _initialize_call_async,
            tenant_id=tenant_id,
            call_sid=CallSid,
            caller_phone=From
        )
        
        logger.info("Async voice call initiated", tenant_id=tenant_id, call_sid=CallSid)
        return PlainTextResponse(content=str(twiml), media_type="application/xml")
        
    except Exception as e:
        logger.error("Async voice call handling failed", error=str(e), tenant_id=tenant_id)
        
        # Return error TwiML
        error_twiml = create_twiml_response(
            message="I'm sorry, we're experiencing technical difficulties. Please call back later.",
            hangup=True
        )
        return PlainTextResponse(content=str(error_twiml), media_type="application/xml")


@router.post("/{tenant_id}/process-async")
async def process_voice_input_async(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    SpeechResult: str = Form(None),
    RecordingUrl: str = Form(None),
    CallSid: str = Form(None),
    From: str = Form(None),
) -> PlainTextResponse:
    """
    Process voice input with async Celery tasks
    
    Queues the AI processing and returns either:
    1. Processing message while waiting for results
    2. Completed response if processing is fast enough
    """
    try:
        logger.info(
            "Processing async voice input",
            tenant_id=tenant_id,
            call_sid=CallSid,
            has_speech=bool(SpeechResult),
            has_recording=bool(RecordingUrl)
        )
        
        # Validate request
        if not await validate_twilio_signature(request):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Get tenant and voice config
        tenant = await TenantService.validate_tenant_access(db, tenant_id=tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        voice_config = await TenantService.get_voice_config(db, tenant_id)
        if not voice_config:
            raise HTTPException(status_code=404, detail="Voice configuration not found")
        
        # Handle input type
        if SpeechResult:
            # Process text input directly (faster)
            return await _process_text_input_async(
                tenant_id=tenant_id,
                text_input=SpeechResult,
                call_sid=CallSid,
                caller_phone=From,
                voice_config=voice_config
            )
        elif RecordingUrl:
            # Queue audio processing task
            return await _process_audio_input_async(
                tenant_id=tenant_id,
                recording_url=RecordingUrl,
                call_sid=CallSid,
                caller_phone=From,
                voice_config=voice_config
            )
        else:
            # No input received
            twiml = create_twiml_response(
                message="I didn't receive any input. Could you please try again?",
                voice=voice_config.voice_name,
                next_action_url=f"/api/v1/voice/{tenant_id}/process-async",
                gather_timeout=10
            )
            return PlainTextResponse(content=str(twiml), media_type="application/xml")
        
    except Exception as e:
        logger.error("Async voice processing failed", error=str(e), tenant_id=tenant_id)
        
        # Return error response
        error_twiml = create_twiml_response(
            message="I'm having trouble processing your request. Let me connect you with someone who can help.",
            dial_number="+1234567890",  # Replace with actual support number
            hangup=True
        )
        return PlainTextResponse(content=str(error_twiml), media_type="application/xml")


@router.post("/{tenant_id}/check-result/{task_id}")
async def check_processing_result(
    tenant_id: str,
    task_id: str,
    request: Request,
    CallSid: str = Form(None),
) -> PlainTextResponse:
    """
    Check result of async processing task
    
    This endpoint is called by TwiML redirect after a processing delay
    to get the final AI response.
    """
    try:
        logger.info("Checking processing result", tenant_id=tenant_id, task_id=task_id)
        
        # Get task status
        task_status = get_voice_task_status(task_id)
        
        if task_status["status"] == "SUCCESS":
            # Task completed successfully
            result = task_status["result"]
            
            if result.get("transfer_to_human"):
                twiml = create_twiml_response(
                    message=result["text_response"],
                    dial_number="+1234567890",
                    hangup=True
                )
            else:
                # Decode audio response
                if result.get("audio_data_base64"):
                    # For now, just use text response
                    # In production, you'd serve the audio file
                    pass
                
                twiml = create_twiml_response(
                    message=result["text_response"],
                    voice="nova",  # Use default voice
                    next_action_url=f"/api/v1/voice/{tenant_id}/process-async",
                    gather_timeout=10
                )
        
        elif task_status["status"] == "FAILURE":
            # Task failed
            twiml = create_twiml_response(
                message="I'm sorry, I encountered an error processing your request. Let me transfer you to someone who can help.",
                dial_number="+1234567890",
                hangup=True
            )
        
        else:
            # Task still processing - ask caller to wait
            twiml = create_twiml_response(
                message="I'm still processing your request. Please hold on just a moment.",
                next_action_url=f"/api/v1/voice/{tenant_id}/check-result/{task_id}",
                gather_input=False
            )
            # Add delay before redirect
            import time
            time.sleep(2)
        
        return PlainTextResponse(content=str(twiml), media_type="application/xml")
        
    except Exception as e:
        logger.error("Result check failed", error=str(e), task_id=task_id)
        
        # Return error response
        error_twiml = create_twiml_response(
            message="I'm sorry, there was an error. Please call back later.",
            hangup=True
        )
        return PlainTextResponse(content=str(error_twiml), media_type="application/xml")


# Helper functions

async def _initialize_call_async(
    tenant_id: str,
    call_sid: str,
    caller_phone: str
):
    """Initialize call in background"""
    try:
        # This would create initial call log entry, customer record, etc.
        logger.info("Initializing call async", tenant_id=tenant_id, call_sid=call_sid)
        
        # Add any initialization logic here
        pass
        
    except Exception as e:
        logger.error("Call initialization failed", error=str(e))


async def _process_text_input_async(
    tenant_id: str,
    text_input: str,
    call_sid: str,
    caller_phone: str,
    voice_config
) -> PlainTextResponse:
    """Process text input with fast response"""
    
    try:
        # For simple text input, we can process faster
        # Queue the processing task
        task = process_voice_async.delay(
            tenant_id=tenant_id,
            audio_data_base64="",  # No audio data for text input
            call_sid=call_sid,
            caller_phone=caller_phone,
            conversation_history=[]
        )
        
        # Return processing message with redirect to check result
        twiml = create_twiml_response(
            message="Let me think about that for a moment...",
            next_action_url=f"/api/v1/voice/{tenant_id}/check-result/{task.id}",
            gather_input=False
        )
        
        return PlainTextResponse(content=str(twiml), media_type="application/xml")
        
    except Exception as e:
        logger.error("Text input processing failed", error=str(e))
        raise


async def _process_audio_input_async(
    tenant_id: str,
    recording_url: str,
    call_sid: str,
    caller_phone: str,
    voice_config
) -> PlainTextResponse:
    """Process audio input with async task"""
    
    try:
        # Download audio first
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(recording_url)
            audio_data = response.content
        
        # Encode for Celery task
        audio_data_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Queue the processing task
        task = process_voice_async.delay(
            tenant_id=tenant_id,
            audio_data_base64=audio_data_base64,
            call_sid=call_sid,
            caller_phone=caller_phone,
            conversation_history=[]
        )
        
        # Return processing message
        twiml = create_twiml_response(
            message="I'm processing your message, please hold on...",
            next_action_url=f"/api/v1/voice/{tenant_id}/check-result/{task.id}",
            gather_input=False
        )
        
        return PlainTextResponse(content=str(twiml), media_type="application/xml")
        
    except Exception as e:
        logger.error("Audio input processing failed", error=str(e))
        raise