"""
AI Service for OpenAI integration
Handles speech-to-text, language model, and text-to-speech operations
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import httpx
from openai import AsyncOpenAI
from langdetect import detect, DetectorFactory
import structlog

from app.core.config import settings
from app.models.voice_config import VoiceConfig

# Set seed for consistent language detection
DetectorFactory.seed = 0

logger = structlog.get_logger(__name__)


class AIService:
    """
    AI service for handling all OpenAI interactions
    
    Features:
    - Async OpenAI client
    - Speech-to-text transcription
    - GPT conversation processing
    - Text-to-speech generation
    - Language detection and processing
    - PII redaction for logging
    """
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.http_client = httpx.AsyncClient()
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = None,
        tenant_id: str = None
    ) -> Tuple[str, str]:
        """
        Transcribe audio to text using OpenAI Whisper
        
        Args:
            audio_data: Raw audio bytes
            language: Language code (optional, auto-detect if None)
            tenant_id: Tenant ID for logging
            
        Returns:
            Tuple of (transcribed_text, detected_language)
        """
        try:
            logger.info("Starting audio transcription", tenant_id=tenant_id)
            
            # Create temporary file for OpenAI API
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Transcribe using OpenAI Whisper
                with open(temp_file_path, "rb") as audio_file:
                    transcript = await self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="json",
                        language=language if language else None
                    )
                
                transcribed_text = transcript.text.strip()
                detected_language = language or "en"  # Default to English if not specified
                
                # Try to detect language if not provided
                if not language and transcribed_text:
                    try:
                        detected_language = detect(transcribed_text)
                    except:
                        detected_language = "en"
                
                logger.info(
                    "Audio transcription completed",
                    tenant_id=tenant_id,
                    text_length=len(transcribed_text),
                    detected_language=detected_language,
                    transcribed_text=self._redact_pii(transcribed_text)
                )
                
                return transcribed_text, detected_language
                
            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error("Audio transcription failed", error=str(e), tenant_id=tenant_id)
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def process_conversation(
        self,
        user_input: str,
        voice_config: VoiceConfig,
        conversation_history: List[Dict] = None,
        tenant_id: str = None,
        customer_context: Dict = None
    ) -> Tuple[str, float]:
        """
        Process user input and generate AI response
        
        Args:
            user_input: User's spoken message
            voice_config: Tenant's voice configuration
            conversation_history: Previous conversation turns
            tenant_id: Tenant ID for logging
            customer_context: Customer information for personalization
            
        Returns:
            Tuple of (ai_response, confidence_score)
        """
        try:
            logger.info(
                "Processing conversation turn",
                tenant_id=tenant_id,
                user_input=self._redact_pii(user_input),
                ai_model=voice_config.ai_model
            )
            
            # Build conversation messages
            messages = self._build_conversation_messages(
                user_input=user_input,
                voice_config=voice_config,
                conversation_history=conversation_history or [],
                customer_context=customer_context
            )
            
            # Call OpenAI GPT
            response = await self.openai_client.chat.completions.create(
                model=voice_config.ai_model,
                messages=messages,
                max_tokens=voice_config.ai_max_tokens,
                temperature=float(voice_config.ai_temperature),
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Calculate confidence score (simplified - OpenAI doesn't provide this directly)
            confidence = self._calculate_confidence(ai_response, user_input)
            
            logger.info(
                "Conversation processing completed",
                tenant_id=tenant_id,
                ai_response=self._redact_pii(ai_response),
                confidence=confidence,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
            return ai_response, confidence
            
        except Exception as e:
            logger.error("Conversation processing failed", error=str(e), tenant_id=tenant_id)
            raise Exception(f"AI processing failed: {str(e)}")
    
    async def generate_speech(
        self,
        text: str,
        voice_config: VoiceConfig,
        tenant_id: str = None
    ) -> bytes:
        """
        Generate speech audio from text using OpenAI TTS
        
        Args:
            text: Text to convert to speech
            voice_config: Voice configuration settings
            tenant_id: Tenant ID for logging
            
        Returns:
            Audio bytes (MP3 format)
        """
        try:
            logger.info(
                "Generating speech audio",
                tenant_id=tenant_id,
                text_length=len(text),
                voice_name=voice_config.voice_name,
                text_preview=self._redact_pii(text[:100])
            )
            
            # OpenAI TTS API call
            response = await self.openai_client.audio.speech.create(
                model="tts-1",  # or "tts-1-hd" for higher quality
                voice=self._map_voice_name(voice_config.voice_name),
                input=text,
                speed=float(voice_config.voice_speed)
            )
            
            # Get audio bytes
            audio_bytes = response.content
            
            logger.info(
                "Speech generation completed",
                tenant_id=tenant_id,
                audio_size_kb=len(audio_bytes) / 1024
            )
            
            return audio_bytes
            
        except Exception as e:
            logger.error("Speech generation failed", error=str(e), tenant_id=tenant_id)
            raise Exception(f"TTS generation failed: {str(e)}")
    
    def _build_conversation_messages(
        self,
        user_input: str,
        voice_config: VoiceConfig,
        conversation_history: List[Dict],
        customer_context: Dict = None
    ) -> List[Dict]:
        """Build message array for OpenAI chat completion"""
        
        messages = []
        
        # System prompt
        system_prompt = voice_config.get_system_prompt()
        
        # Add customer context if available
        if customer_context:
            system_prompt += f"\n\nCustomer context: {customer_context.get('name', 'Unknown')} customer, "
            system_prompt += f"phone: {customer_context.get('phone', 'Unknown')[:3]}***, "
            system_prompt += f"previous calls: {customer_context.get('total_calls', 0)}"
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (last 10 turns to stay within token limits)
        recent_history = conversation_history[-10:] if conversation_history else []
        for turn in recent_history:
            if turn.get("user_input"):
                messages.append({"role": "user", "content": turn["user_input"]})
            if turn.get("ai_response"):
                messages.append({"role": "assistant", "content": turn["ai_response"]})
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _calculate_confidence(self, ai_response: str, user_input: str) -> float:
        """
        Calculate confidence score for AI response
        This is a simplified heuristic since OpenAI doesn't provide confidence directly
        """
        confidence = 0.8  # Base confidence
        
        # Lower confidence for very short responses
        if len(ai_response.strip()) < 20:
            confidence -= 0.2
        
        # Lower confidence for generic responses
        generic_phrases = [
            "i'm sorry", "i don't understand", "could you repeat",
            "can you clarify", "i'm not sure"
        ]
        if any(phrase in ai_response.lower() for phrase in generic_phrases):
            confidence -= 0.3
        
        # Higher confidence for specific responses with appointments/times
        specific_indicators = [
            "appointment", "schedule", "available", "book", "confirm",
            "monday", "tuesday", "wednesday", "thursday", "friday",
            "morning", "afternoon", "evening", "am", "pm"
        ]
        if any(indicator in ai_response.lower() for indicator in specific_indicators):
            confidence += 0.1
        
        # Ensure confidence is between 0 and 1
        return max(0.1, min(1.0, confidence))
    
    def _map_voice_name(self, voice_name: str) -> str:
        """Map custom voice names to OpenAI TTS voices"""
        voice_mapping = {
            "Rachel": "nova",
            "Sarah": "alloy", 
            "Michael": "echo",
            "Emma": "shimmer",
            "James": "onyx",
            "Sophia": "fable"
        }
        return voice_mapping.get(voice_name, "nova")  # Default to nova
    
    def _redact_pii(self, text: str) -> str:
        """Redact personally identifiable information from text for logging"""
        if not text:
            return text
        
        # Phone number patterns
        text = re.sub(r'\b(\d{3}[-.]?\d{3}[-.]?\d{4})\b', '[PHONE]', text)
        
        # Email patterns  
        text = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[EMAIL]', text)
        
        # SSN patterns
        text = re.sub(r'\b\d{3}-?\d{2}-?\d{4}\b', '[SSN]', text)
        
        # Credit card patterns (simple)
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
        
        # Names (this is tricky, so we'll be conservative)
        # Only redact if it looks like "My name is John" pattern
        text = re.sub(r'(my name is|i\'m|i am)\s+([A-Z][a-z]+)', r'\1 [NAME]', text, flags=re.IGNORECASE)
        
        return text
    
    def detect_appointment_intent(self, text: str) -> Dict:
        """
        Detect if user wants to schedule/cancel/modify appointments
        
        Returns:
            Dict with intent and extracted information
        """
        text_lower = text.lower()
        
        # Schedule intent
        schedule_keywords = [
            "schedule", "book", "appointment", "reserve", "set up", "make an appointment",
            "need to see", "want to come in", "available", "when can i"
        ]
        
        # Cancel intent
        cancel_keywords = [
            "cancel", "reschedule", "move", "change", "postpone", "different time"
        ]
        
        # Time extraction patterns
        time_patterns = [
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(\d{1,2}:\d{2})\s*(am|pm)?\b',
            r'\b(\d{1,2})\s*(am|pm)\b',
            r'\b(morning|afternoon|evening|noon)\b',
            r'\b(next week|this week|tomorrow|today)\b'
        ]
        
        result = {
            "intent": "unknown",
            "confidence": 0.0,
            "extracted_info": {}
        }
        
        if any(keyword in text_lower for keyword in schedule_keywords):
            result["intent"] = "schedule"
            result["confidence"] = 0.8
        elif any(keyword in text_lower for keyword in cancel_keywords):
            result["intent"] = "cancel_reschedule"  
            result["confidence"] = 0.8
        
        # Extract time information
        extracted_times = []
        for pattern in time_patterns:
            matches = re.findall(pattern, text_lower)
            extracted_times.extend(matches)
        
        if extracted_times:
            result["extracted_info"]["time_references"] = extracted_times
            result["confidence"] += 0.1
        
        return result