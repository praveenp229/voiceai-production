"""
Voice API endpoints for Twilio webhook integration
Handles incoming voice calls, audio processing, and TwiML responses
"""

import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.services.voice_service import VoiceService
from app.services.tenant_service import TenantService
from app.utils.twilio_utils import validate_twilio_signature, create_twiml_response

logger = structlog.get_logger(__name__)

router = APIRouter()
voice_service = VoiceService()


@router.post("/{tenant_id}")
async def handle_voice_call(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    From: str = Form(None),
    To: str = Form(None),
    CallSid: str = Form(None),
    CallStatus: str = Form(None),
) -> PlainTextResponse:
    """
    Handle incoming Twilio voice calls
    
    This endpoint receives Twilio webhook calls when a phone call starts.
    It returns TwiML instructions to begin the conversation.
    """
    try:
        logger.info(
            "Incoming voice call",
            tenant_id=tenant_id,
            call_sid=CallSid,
            caller=f"{From[:3]}***" if From else "Unknown",
            status=CallStatus
        )
        
        # Validate Twilio signature
        if not await validate_twilio_signature(request):
            logger.error("Invalid Twilio signature", tenant_id=tenant_id, call_sid=CallSid)
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Get tenant and validate
        tenant = await TenantService.validate_tenant_access(db, tenant_id=tenant_id)
        if not tenant:
            logger.error("Invalid tenant", tenant_id=tenant_id)
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Get voice configuration
        voice_config = await TenantService.get_voice_config(db, tenant_id)
        if not voice_config:
            logger.error("Voice config not found", tenant_id=tenant_id)
            raise HTTPException(status_code=404, detail="Voice configuration not found")
        
        # Start conversation and get greeting
        greeting_result = await voice_service.start_conversation(
            db=db,
            tenant=tenant,
            voice_config=voice_config,
            caller_phone=From
        )
        
        # Create TwiML response with greeting
        twiml = create_twiml_response(
            message=greeting_result["text_response"],
            voice=voice_config.voice_name,
            next_action_url=f"/api/v1/voice/{tenant_id}/gather",
            gather_timeout=10
        )
        
        logger.info("Voice call initiated", tenant_id=tenant_id, call_sid=CallSid)
        return PlainTextResponse(content=str(twiml), media_type="application/xml")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Voice call handling failed", error=str(e), tenant_id=tenant_id, call_sid=CallSid)
        
        # Return error TwiML
        error_twiml = create_twiml_response(
            message="I'm sorry, we're experiencing technical difficulties. Please call back later.",
            hangup=True
        )
        return PlainTextResponse(content=str(error_twiml), media_type="application/xml")


@router.post("/{tenant_id}/gather")
async def handle_voice_gather(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    SpeechResult: str = Form(None),
    RecordingUrl: str = Form(None),
    CallSid: str = Form(None),
    From: str = Form(None),
) -> PlainTextResponse:
    """
    Handle Twilio speech input gathering
    
    This endpoint receives speech input from Twilio and processes it
    through the AI pipeline to generate responses.
    """
    try:
        logger.info(
            "Processing voice input",
            tenant_id=tenant_id,
            call_sid=CallSid,
            has_speech=bool(SpeechResult),
            has_recording=bool(RecordingUrl)
        )
        
        # Validate Twilio signature
        if not await validate_twilio_signature(request):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Get tenant and voice config
        tenant = await TenantService.validate_tenant_access(db, tenant_id=tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        voice_config = await TenantService.get_voice_config(db, tenant_id)
        if not voice_config:
            raise HTTPException(status_code=404, detail="Voice configuration not found")
        
        # Handle speech input
        if SpeechResult:
            # Process text input directly
            response_result = await _process_text_input(
                db=db,
                tenant=tenant,
                voice_config=voice_config,
                text_input=SpeechResult,
                call_sid=CallSid,
                caller_phone=From
            )
        elif RecordingUrl:
            # Download and process audio recording
            response_result = await _process_audio_recording(
                db=db,
                tenant=tenant,
                voice_config=voice_config,
                recording_url=RecordingUrl,
                call_sid=CallSid,
                caller_phone=From
            )
        else:
            # No input received
            response_result = {
                "text_response": "I didn't receive any input. Could you please try again?",
                "transfer_to_human": False
            }
        
        # Check if we need to transfer to human
        if response_result.get("transfer_to_human"):
            twiml = create_twiml_response(
                message=response_result["text_response"],
                dial_number="+1234567890",  # Replace with actual transfer number
                hangup=True
            )
        else:
            # Continue conversation
            twiml = create_twiml_response(
                message=response_result["text_response"],
                voice=voice_config.voice_name,
                next_action_url=f"/api/v1/voice/{tenant_id}/gather",
                gather_timeout=10
            )
        
        logger.info("Voice input processed successfully", tenant_id=tenant_id, call_sid=CallSid)
        return PlainTextResponse(content=str(twiml), media_type="application/xml")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Voice input processing failed", error=str(e), tenant_id=tenant_id, call_sid=CallSid)
        
        # Return error response
        error_twiml = create_twiml_response(
            message="I'm having trouble processing your request. Let me connect you with someone who can help.",
            dial_number="+1234567890",  # Replace with actual support number
            hangup=True
        )
        return PlainTextResponse(content=str(error_twiml), media_type="application/xml")


@router.post("/{tenant_id}/status")
async def handle_call_status(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    CallSid: str = Form(None),
    CallStatus: str = Form(None),
    CallDuration: str = Form(None),
) -> Response:
    """
    Handle Twilio call status updates
    
    This endpoint receives status updates about call progress
    (answered, completed, failed, etc.)
    """
    try:
        logger.info(
            "Call status update",
            tenant_id=tenant_id,
            call_sid=CallSid,
            status=CallStatus,
            duration=CallDuration
        )
        
        # Update call log with final status
        if CallSid and CallStatus:
            await _update_call_status(db, CallSid, CallStatus, CallDuration)
        
        return Response(status_code=200)
        
    except Exception as e:
        logger.error("Call status update failed", error=str(e), tenant_id=tenant_id, call_sid=CallSid)
        return Response(status_code=200)  # Return 200 to avoid Twilio retries


@router.post("/{tenant_id}/recording")
async def handle_recording(
    tenant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    CallSid: str = Form(None),
    RecordingUrl: str = Form(None),
    RecordingDuration: str = Form(None),
) -> Response:
    """
    Handle Twilio call recordings
    
    This endpoint receives recording URLs after calls are completed
    """
    try:
        logger.info(
            "Call recording received",
            tenant_id=tenant_id,
            call_sid=CallSid,
            recording_url=RecordingUrl,
            duration=RecordingDuration
        )
        
        # Store recording URL in call log
        if CallSid and RecordingUrl:
            await _update_call_recording(db, CallSid, RecordingUrl)
        
        return Response(status_code=200)
        
    except Exception as e:
        logger.error("Recording handling failed", error=str(e), tenant_id=tenant_id, call_sid=CallSid)
        return Response(status_code=200)


# Helper functions

async def _process_text_input(
    db: AsyncSession,
    tenant,
    voice_config,
    text_input: str,
    call_sid: str,
    caller_phone: str
) -> dict:
    """Process text input through AI pipeline"""
    
    # Create mock audio data for the voice service
    # In a real implementation, this would be actual audio bytes
    mock_audio = b"mock_audio_data"
    
    return await voice_service.process_voice_turn(
        db=db,
        tenant=tenant,
        voice_config=voice_config,
        audio_data=mock_audio,
        call_sid=call_sid,
        caller_phone=caller_phone,
        conversation_history=[]  # TODO: Retrieve actual history
    )


async def _process_audio_recording(
    db: AsyncSession,
    tenant,
    voice_config,
    recording_url: str,
    call_sid: str,
    caller_phone: str
) -> dict:
    """Download and process audio recording"""
    
    try:
        # Download audio from Twilio
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(recording_url)
            audio_data = response.content
        
        return await voice_service.process_voice_turn(
            db=db,
            tenant=tenant,
            voice_config=voice_config,
            audio_data=audio_data,
            call_sid=call_sid,
            caller_phone=caller_phone,
            conversation_history=[]  # TODO: Retrieve actual history
        )
        
    except Exception as e:
        logger.error("Audio recording processing failed", error=str(e))
        return {
            "text_response": "I'm having trouble processing your audio. Could you please repeat that?",
            "transfer_to_human": False
        }


async def _update_call_status(
    db: AsyncSession,
    call_sid: str,
    call_status: str,
    call_duration: str = None
):
    """Update call log with status information"""
    
    try:
        from sqlalchemy import select, update
        from app.models.call_log import CallLog
        from datetime import datetime, timezone
        
        # Update call log
        stmt = (
            update(CallLog)
            .where(CallLog.call_sid == call_sid)
            .values(
                call_status=call_status,
                call_duration=int(call_duration) if call_duration else None,
                ended_at=datetime.now(timezone.utc) if call_status == "completed" else None,
                call_successful=call_status == "completed"
            )
        )
        
        await db.execute(stmt)
        await db.commit()
        
        logger.info("Call status updated", call_sid=call_sid, status=call_status)
        
    except Exception as e:
        logger.error("Failed to update call status", error=str(e), call_sid=call_sid)


async def _update_call_recording(
    db: AsyncSession,
    call_sid: str,
    recording_url: str
):
    """Update call log with recording URL"""
    
    try:
        from sqlalchemy import update
        from app.models.call_log import CallLog
        
        stmt = (
            update(CallLog)
            .where(CallLog.call_sid == call_sid)
            .values(audio_url=recording_url)
        )
        
        await db.execute(stmt)
        await db.commit()
        
        logger.info("Call recording URL updated", call_sid=call_sid)
        
    except Exception as e:
        logger.error("Failed to update recording URL", error=str(e), call_sid=call_sid)