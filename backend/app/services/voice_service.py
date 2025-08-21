"""
Voice service for handling complete voice interaction flows
Orchestrates STT, AI processing, and TTS operations
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.services.ai_service import AIService
from app.services.sms_service import SMSService
from app.services.calendar_service import CalendarService
from app.models.call_log import CallLog
from app.models.customer import Customer
from app.models.voice_config import VoiceConfig
from app.models.tenant import Tenant

logger = structlog.get_logger(__name__)


class VoiceService:
    """
    Voice service orchestrator for complete conversation flows
    
    Features:
    - End-to-end voice processing
    - Conversation state management
    - Customer identification and tracking
    - Appointment intent detection
    - Error handling and fallbacks
    """
    
    def __init__(self):
        self.ai_service = AIService()
        self.sms_service = SMSService()
        self.calendar_service = CalendarService()
    
    async def process_voice_turn(
        self,
        db: AsyncSession,
        tenant: Tenant,
        voice_config: VoiceConfig,
        audio_data: bytes,
        call_sid: str,
        caller_phone: str,
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        Process a complete voice interaction turn
        
        Args:
            db: Database session
            tenant: Tenant object
            voice_config: Voice configuration
            audio_data: Raw audio bytes from Twilio
            call_sid: Twilio call SID
            caller_phone: Caller's phone number
            conversation_history: Previous conversation turns
            
        Returns:
            Dict with response audio, text, and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(
                "Processing voice turn",
                tenant_id=tenant.id,
                call_sid=call_sid,
                caller_phone=f"{caller_phone[:3]}***"
            )
            
            # Get or create customer
            customer = await self._get_or_create_customer(
                db, tenant.id, caller_phone
            )
            
            # Get or create call log
            call_log = await self._get_or_create_call_log(
                db, tenant.id, customer.id, call_sid, caller_phone
            )
            
            # Step 1: Transcribe audio
            transcribed_text, detected_language = await self.ai_service.transcribe_audio(
                audio_data=audio_data,
                language=voice_config.primary_language,
                tenant_id=tenant.id
            )
            
            if not transcribed_text.strip():
                return await self._handle_empty_input(voice_config, tenant.id)
            
            # Step 2: Check for confusion or test input
            if self._is_confused_input(transcribed_text):
                return await self._handle_confused_input(voice_config, tenant.id)
            
            # Step 3: Process with AI
            customer_context = {
                "name": customer.name,
                "phone": customer.phone,
                "total_calls": customer.total_calls
            }
            
            ai_response, confidence = await self.ai_service.process_conversation(
                user_input=transcribed_text,
                voice_config=voice_config,
                conversation_history=conversation_history or [],
                tenant_id=tenant.id,
                customer_context=customer_context
            )
            
            # Step 4: Check confidence and handle fallback
            if confidence < float(voice_config.confidence_threshold):
                if voice_config.fallback_to_human:
                    return await self._handle_low_confidence(
                        voice_config, transcribed_text, confidence, tenant.id
                    )
            
            # Step 5: Detect appointment intent
            appointment_intent = self.ai_service.detect_appointment_intent(transcribed_text)
            
            # Step 6: Handle appointment scheduling if needed
            if appointment_intent["intent"] == "schedule" and appointment_intent["confidence"] > 0.7:
                ai_response = await self._enhance_response_with_scheduling(
                    db, tenant, customer, ai_response, appointment_intent
                )
            
            # Step 7: Generate TTS audio
            response_audio = await self.ai_service.generate_speech(
                text=ai_response,
                voice_config=voice_config,
                tenant_id=tenant.id
            )
            
            # Step 8: Update call log
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            call_log.add_turn(
                user_input=transcribed_text,
                ai_response=ai_response,
                response_time=processing_time,
                confidence=confidence
            )
            call_log.language_detected = detected_language
            
            # Update customer
            customer.last_call_at = datetime.now(timezone.utc)
            customer.total_calls = str(int(customer.total_calls) + 1)
            
            await db.commit()
            
            logger.info(
                "Voice turn completed successfully",
                tenant_id=tenant.id,
                call_sid=call_sid,
                processing_time=processing_time,
                confidence=confidence,
                intent=appointment_intent["intent"]
            )
            
            return {
                "success": True,
                "audio_data": response_audio,
                "text_response": ai_response,
                "user_input": transcribed_text,
                "confidence": confidence,
                "processing_time": processing_time,
                "language": detected_language,
                "appointment_intent": appointment_intent,
                "call_log_id": call_log.id
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(
                "Voice turn processing failed",
                error=str(e),
                tenant_id=tenant.id,
                call_sid=call_sid
            )
            
            # Return error response
            return {
                "success": False,
                "error": str(e),
                "audio_data": await self._generate_error_audio(voice_config),
                "text_response": "I'm sorry, I'm having technical difficulties. Please try again or speak with a human representative."
            }
    
    async def start_conversation(
        self,
        db: AsyncSession,
        tenant: Tenant,
        voice_config: VoiceConfig,
        caller_phone: str
    ) -> Dict:
        """
        Start a new conversation with greeting
        
        Returns:
            Dict with greeting audio and text
        """
        try:
            logger.info("Starting new conversation", tenant_id=tenant.id, caller_phone=f"{caller_phone[:3]}***")
            
            # Get greeting message
            greeting_text = voice_config.get_greeting_message()
            
            # Generate greeting audio
            greeting_audio = await self.ai_service.generate_speech(
                text=greeting_text,
                voice_config=voice_config,
                tenant_id=tenant.id
            )
            
            return {
                "success": True,
                "audio_data": greeting_audio,
                "text_response": greeting_text,
                "is_greeting": True
            }
            
        except Exception as e:
            logger.error("Failed to start conversation", error=str(e), tenant_id=tenant.id)
            
            # Fallback greeting
            fallback_text = "Thank you for calling. How may I help you today?"
            return {
                "success": False,
                "audio_data": None,
                "text_response": fallback_text,
                "error": str(e)
            }
    
    async def _get_or_create_customer(
        self,
        db: AsyncSession,
        tenant_id: str,
        caller_phone: str
    ) -> Customer:
        """Get existing customer or create new one"""
        from sqlalchemy import select
        
        # Try to find existing customer
        result = await db.execute(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.phone == caller_phone
            )
        )
        customer = result.scalar_one_or_none()
        
        if customer:
            return customer
        
        # Create new customer
        customer = Customer(
            tenant_id=tenant_id,
            name="Unknown Caller",  # Will be updated when we get their name
            phone=caller_phone,
            total_calls="0"
        )
        
        db.add(customer)
        await db.flush()  # Get the customer ID
        
        logger.info("New customer created", tenant_id=tenant_id, customer_id=customer.id)
        return customer
    
    async def _get_or_create_call_log(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        call_sid: str,
        caller_phone: str
    ) -> CallLog:
        """Get existing call log or create new one"""
        from sqlalchemy import select
        
        # Try to find existing call log
        result = await db.execute(
            select(CallLog).where(CallLog.call_sid == call_sid)
        )
        call_log = result.scalar_one_or_none()
        
        if call_log:
            return call_log
        
        # Create new call log
        call_log = CallLog(
            tenant_id=tenant_id,
            customer_id=customer_id,
            call_sid=call_sid,
            caller_phone=caller_phone,
            started_at=datetime.now(timezone.utc)
        )
        
        db.add(call_log)
        await db.flush()
        
        logger.info("New call log created", call_log_id=call_log.id, call_sid=call_sid)
        return call_log
    
    def _is_confused_input(self, text: str) -> bool:
        """Check if input seems confused or invalid"""
        text_clean = text.strip().lower()
        
        # Too short
        if len(text_clean) < 3:
            return True
        
        # Test phrases
        test_phrases = [
            'test', 'testing', '123', 'hello test', 'check check',
            'one two three', 'can you hear me'
        ]
        
        return text_clean in test_phrases
    
    async def _handle_empty_input(self, voice_config: VoiceConfig, tenant_id: str) -> Dict:
        """Handle empty or no audio input"""
        response_text = "I didn't catch that. Could you please repeat what you need help with?"
        
        response_audio = await self.ai_service.generate_speech(
            text=response_text,
            voice_config=voice_config,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "audio_data": response_audio,
            "text_response": response_text,
            "confidence": 0.5,
            "needs_retry": True
        }
    
    async def _handle_confused_input(self, voice_config: VoiceConfig, tenant_id: str) -> Dict:
        """Handle confused or test input"""
        response_text = "I'm here to help with your dental appointment needs. How can I assist you today?"
        
        response_audio = await self.ai_service.generate_speech(
            text=response_text,
            voice_config=voice_config,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "audio_data": response_audio,
            "text_response": response_text,
            "confidence": 0.6,
            "is_clarification": True
        }
    
    async def _handle_low_confidence(
        self,
        voice_config: VoiceConfig,
        user_input: str,
        confidence: float,
        tenant_id: str
    ) -> Dict:
        """Handle low confidence responses"""
        response_text = "I want to make sure I help you correctly. Let me transfer you to one of our team members who can better assist you."
        
        response_audio = await self.ai_service.generate_speech(
            text=response_text,
            voice_config=voice_config,
            tenant_id=tenant_id
        )
        
        return {
            "success": True,
            "audio_data": response_audio,
            "text_response": response_text,
            "confidence": confidence,
            "transfer_to_human": True,
            "low_confidence": True
        }
    
    async def _enhance_response_with_scheduling(
        self,
        db: AsyncSession,
        tenant: Tenant,
        customer: Customer,
        ai_response: str,
        appointment_intent: Dict
    ) -> str:
        """Enhance AI response with actual scheduling information"""
        try:
            # Check available slots (simplified)
            available_slots = await self.calendar_service.get_available_slots(
                tenant_id=tenant.id,
                days_ahead=7
            )
            
            if available_slots:
                slot_text = ", ".join(available_slots[:3])  # Show first 3 slots
                ai_response += f" I have these times available: {slot_text}. Which would work best for you?"
            else:
                ai_response += " Let me check our availability and get back to you with some options."
            
            return ai_response
            
        except Exception as e:
            logger.error("Failed to enhance response with scheduling", error=str(e))
            return ai_response
    
    async def _generate_error_audio(self, voice_config: VoiceConfig) -> bytes:
        """Generate audio for error scenarios"""
        try:
            error_text = "I'm sorry, I'm experiencing technical difficulties. Please try again."
            return await self.ai_service.generate_speech(
                text=error_text,
                voice_config=voice_config
            )
        except:
            # Return empty bytes if even error audio generation fails
            return b""