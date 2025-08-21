"""
Voice processing tasks for Celery
Async tasks for AI operations, transcription, and TTS generation
"""

import asyncio
import json
from typing import Dict, List, Optional
from celery import current_task
import structlog

from app.tasks.celery_app import celery_app
from app.services.ai_service import AIService
from app.services.voice_service import VoiceService
from app.services.tenant_service import TenantService
from app.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="process_voice_async",
    max_retries=3,
    default_retry_delay=10,
    queue="voice"
)
def process_voice_async(
    self,
    tenant_id: str,
    audio_data_base64: str,
    call_sid: str,
    caller_phone: str,
    conversation_history: List[Dict] = None
):
    """
    Process voice audio asynchronously
    
    Args:
        self: Celery task instance
        tenant_id: Tenant ID
        audio_data_base64: Base64 encoded audio data
        call_sid: Twilio call SID
        caller_phone: Caller's phone number
        conversation_history: Previous conversation turns
        
    Returns:
        Dict with processing results
    """
    try:
        logger.info(
            "Starting async voice processing",
            task_id=self.request.id,
            tenant_id=tenant_id,
            call_sid=call_sid,
            caller_phone=f"{caller_phone[:3]}***"
        )
        
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={"status": "Decoding audio data"}
        )
        
        # Decode audio data
        import base64
        audio_data = base64.b64decode(audio_data_base64)
        
        # Run async processing in event loop
        result = asyncio.run(_process_voice_internal(
            tenant_id=tenant_id,
            audio_data=audio_data,
            call_sid=call_sid,
            caller_phone=caller_phone,
            conversation_history=conversation_history or [],
            task_id=self.request.id
        ))
        
        logger.info(
            "Voice processing completed",
            task_id=self.request.id,
            tenant_id=tenant_id,
            success=result.get("success", False)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Voice processing failed",
            task_id=self.request.id,
            error=str(e),
            tenant_id=tenant_id
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying voice processing (attempt {self.request.retries + 1})")
            raise self.retry(countdown=self.default_retry_delay * (2 ** self.request.retries))
        
        return {
            "success": False,
            "error": str(e),
            "task_id": self.request.id
        }


@celery_app.task(
    bind=True,
    name="process_conversation_async",
    max_retries=2,
    default_retry_delay=5,
    queue="voice"
)
def process_conversation_async(
    self,
    tenant_id: str,
    user_input: str,
    conversation_history: List[Dict] = None,
    customer_context: Dict = None
):
    """
    Process conversation text with AI asynchronously
    
    Args:
        self: Celery task instance
        tenant_id: Tenant ID
        user_input: User's text input
        conversation_history: Previous conversation turns
        customer_context: Customer information
        
    Returns:
        Dict with AI response and metadata
    """
    try:
        logger.info(
            "Starting async conversation processing",
            task_id=self.request.id,
            tenant_id=tenant_id,
            input_length=len(user_input)
        )
        
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={"status": "Processing with AI"}
        )
        
        # Run async processing
        result = asyncio.run(_process_conversation_internal(
            tenant_id=tenant_id,
            user_input=user_input,
            conversation_history=conversation_history or [],
            customer_context=customer_context or {},
            task_id=self.request.id
        ))
        
        logger.info(
            "Conversation processing completed",
            task_id=self.request.id,
            tenant_id=tenant_id,
            confidence=result.get("confidence", 0)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Conversation processing failed",
            task_id=self.request.id,
            error=str(e),
            tenant_id=tenant_id
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay)
        
        return {
            "success": False,
            "error": str(e),
            "ai_response": "I'm sorry, I'm having technical difficulties. Please try again.",
            "confidence": 0.1
        }


@celery_app.task(
    bind=True,
    name="generate_tts_async",
    max_retries=2,
    default_retry_delay=3,
    queue="voice"
)
def generate_tts_async(
    self,
    tenant_id: str,
    text: str,
    voice_settings: Dict = None
):
    """
    Generate text-to-speech audio asynchronously
    
    Args:
        self: Celery task instance
        tenant_id: Tenant ID
        text: Text to convert to speech
        voice_settings: Voice configuration settings
        
    Returns:
        Dict with base64 encoded audio data
    """
    try:
        logger.info(
            "Starting async TTS generation",
            task_id=self.request.id,
            tenant_id=tenant_id,
            text_length=len(text)
        )
        
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={"status": "Generating speech audio"}
        )
        
        # Run async TTS generation
        result = asyncio.run(_generate_tts_internal(
            tenant_id=tenant_id,
            text=text,
            voice_settings=voice_settings or {},
            task_id=self.request.id
        ))
        
        logger.info(
            "TTS generation completed",
            task_id=self.request.id,
            tenant_id=tenant_id,
            audio_size_kb=len(result.get("audio_data_base64", "")) / 1024 if result.get("success") else 0
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "TTS generation failed",
            task_id=self.request.id,
            error=str(e),
            tenant_id=tenant_id
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay)
        
        return {
            "success": False,
            "error": str(e)
        }


# Internal async functions

async def _process_voice_internal(
    tenant_id: str,
    audio_data: bytes,
    call_sid: str,
    caller_phone: str,
    conversation_history: List[Dict],
    task_id: str
) -> Dict:
    """Internal async voice processing function"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Get tenant and voice config
            tenant = await TenantService.get_tenant_by_id(db, tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            voice_config = await TenantService.get_voice_config(db, tenant_id)
            if not voice_config:
                raise ValueError(f"Voice config for tenant {tenant_id} not found")
            
            # Process voice turn
            voice_service = VoiceService()
            result = await voice_service.process_voice_turn(
                db=db,
                tenant=tenant,
                voice_config=voice_config,
                audio_data=audio_data,
                call_sid=call_sid,
                caller_phone=caller_phone,
                conversation_history=conversation_history
            )
            
            # Add task ID to result
            result["task_id"] = task_id
            
            # Encode audio response as base64 for JSON serialization
            if result.get("audio_data"):
                import base64
                result["audio_data_base64"] = base64.b64encode(result["audio_data"]).decode('utf-8')
                del result["audio_data"]  # Remove binary data
            
            return result
            
        except Exception as e:
            logger.error("Internal voice processing failed", error=str(e), task_id=task_id)
            raise


async def _process_conversation_internal(
    tenant_id: str,
    user_input: str,
    conversation_history: List[Dict],
    customer_context: Dict,
    task_id: str
) -> Dict:
    """Internal async conversation processing function"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Get tenant and voice config
            tenant = await TenantService.get_tenant_by_id(db, tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            voice_config = await TenantService.get_voice_config(db, tenant_id)
            if not voice_config:
                raise ValueError(f"Voice config for tenant {tenant_id} not found")
            
            # Process conversation
            ai_service = AIService()
            ai_response, confidence = await ai_service.process_conversation(
                user_input=user_input,
                voice_config=voice_config,
                conversation_history=conversation_history,
                tenant_id=tenant_id,
                customer_context=customer_context
            )
            
            return {
                "success": True,
                "ai_response": ai_response,
                "confidence": confidence,
                "user_input": user_input,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error("Internal conversation processing failed", error=str(e), task_id=task_id)
            raise


async def _generate_tts_internal(
    tenant_id: str,
    text: str,
    voice_settings: Dict,
    task_id: str
) -> Dict:
    """Internal async TTS generation function"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Get voice config
            voice_config = await TenantService.get_voice_config(db, tenant_id)
            if not voice_config:
                raise ValueError(f"Voice config for tenant {tenant_id} not found")
            
            # Override with provided settings
            if voice_settings:
                for key, value in voice_settings.items():
                    if hasattr(voice_config, key):
                        setattr(voice_config, key, value)
            
            # Generate speech
            ai_service = AIService()
            audio_data = await ai_service.generate_speech(
                text=text,
                voice_config=voice_config,
                tenant_id=tenant_id
            )
            
            # Encode as base64
            import base64
            audio_data_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "success": True,
                "audio_data_base64": audio_data_base64,
                "text": text,
                "voice_settings": voice_settings,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error("Internal TTS generation failed", error=str(e), task_id=task_id)
            raise


# Task status checking functions

def get_voice_task_status(task_id: str) -> Dict:
    """Get status of voice processing task"""
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "meta": result.info if hasattr(result, 'info') else None
    }


def cancel_voice_task(task_id: str) -> bool:
    """Cancel a running voice task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info("Voice task canceled", task_id=task_id)
        return True
    except Exception as e:
        logger.error("Failed to cancel voice task", error=str(e), task_id=task_id)
        return False