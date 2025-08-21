"""
Twilio utilities for webhook validation and TwiML generation
"""

import base64
import hashlib
import hmac
from typing import Optional
from urllib.parse import urlparse, parse_qs
from fastapi import Request
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Dial, Record
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


async def validate_twilio_signature(request: Request) -> bool:
    """
    Validate Twilio webhook signature
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Skip validation in development
        if settings.DEBUG and not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Skipping Twilio signature validation in debug mode")
            return True
        
        if not settings.TWILIO_AUTH_TOKEN:
            logger.error("Twilio auth token not configured")
            return False
        
        # Get signature from headers
        signature = request.headers.get("X-Twilio-Signature")
        if not signature:
            logger.error("Missing Twilio signature header")
            return False
        
        # Get request URL and body
        url = str(request.url)
        body = await request.body()
        
        # Parse form data for validation
        from urllib.parse import parse_qs
        import urllib.parse
        
        if body:
            form_data = parse_qs(body.decode('utf-8'))
            # Flatten the form data for signature validation
            params = []
            for key, values in form_data.items():
                for value in values:
                    params.append(f"{key}{value}")
            data_string = url + "".join(sorted(params))
        else:
            data_string = url
        
        # Calculate expected signature
        expected_signature = base64.b64encode(
            hmac.new(
                settings.TWILIO_AUTH_TOKEN.encode('utf-8'),
                data_string.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')
        
        # Compare signatures
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        if not is_valid:
            logger.error(
                "Invalid Twilio signature",
                provided_signature=signature[:10] + "...",
                expected_signature=expected_signature[:10] + "..."
            )
        
        return is_valid
        
    except Exception as e:
        logger.error("Twilio signature validation failed", error=str(e))
        return False


def create_twiml_response(
    message: str,
    voice: str = "Polly.Joanna",
    gather_input: bool = True,
    gather_timeout: int = 5,
    next_action_url: str = None,
    dial_number: str = None,
    hangup: bool = False,
    record_call: bool = False
) -> VoiceResponse:
    """
    Create TwiML response for voice interactions
    
    Args:
        message: Text message to speak
        voice: Twilio voice to use
        gather_input: Whether to gather user input
        gather_timeout: Timeout for input gathering
        next_action_url: URL to POST input to
        dial_number: Phone number to dial (for transfers)
        hangup: Whether to hang up after message
        record_call: Whether to record the call
        
    Returns:
        TwiML VoiceResponse object
    """
    response = VoiceResponse()
    
    try:
        # Record call if requested
        if record_call:
            response.record(
                max_length=300,  # 5 minutes max
                play_beep=False,
                record_on_hangup=True,
                action="/recording"
            )
        
        # Speak the message
        if message:
            response.say(message, voice=voice)
        
        # Handle call transfer
        if dial_number:
            logger.info("Creating dial TwiML", dial_number=f"{dial_number[:3]}***")
            dial = Dial(
                timeout=30,
                action="/call-status",
                method="POST"
            )
            dial.number(dial_number)
            response.append(dial)
            
            # Say something if dial fails
            response.say("I'm sorry, I couldn't connect you. Please call back later.", voice=voice)
        
        # Gather user input
        elif gather_input and not hangup:
            gather = Gather(
                input="speech",
                timeout=gather_timeout,
                speech_timeout="auto",
                speech_model="phone_call",
                enhanced=True,
                action=next_action_url or "/gather",
                method="POST"
            )
            
            # Add a brief pause to let the user start speaking
            gather.pause(length=1)
            response.append(gather)
            
            # If no input is received, ask again
            response.say("I didn't hear anything. Please let me know how I can help you.", voice=voice)
            response.redirect(next_action_url or "/gather")
        
        # Hang up if requested
        if hangup:
            response.hangup()
        
        logger.debug("TwiML response created", has_gather=gather_input, has_dial=bool(dial_number))
        return response
        
    except Exception as e:
        logger.error("Failed to create TwiML response", error=str(e))
        
        # Return error response
        error_response = VoiceResponse()
        error_response.say("I'm sorry, there was an error. Please call back later.", voice="Polly.Joanna")
        error_response.hangup()
        return error_response


def create_sms_response(message: str) -> str:
    """
    Create TwiML response for SMS
    
    Args:
        message: SMS message to send
        
    Returns:
        TwiML string
    """
    from twilio.twiml.messaging_response import MessagingResponse
    
    response = MessagingResponse()
    response.message(message)
    return str(response)


def extract_phone_number(phone: str) -> str:
    """
    Extract and normalize phone number
    
    Args:
        phone: Raw phone number string
        
    Returns:
        Normalized phone number
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # Add +1 if it's a 10-digit US number
    if len(digits) == 10:
        digits = "1" + digits
    
    # Add + prefix
    if not digits.startswith("+"):
        digits = "+" + digits
    
    return digits


def format_phone_for_display(phone: str) -> str:
    """
    Format phone number for display
    
    Args:
        phone: Phone number string
        
    Returns:
        Formatted phone number
    """
    if not phone:
        return ""
    
    # Extract digits
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) == 11 and digits.startswith('1'):
        # US number: +1 (123) 456-7890
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    elif len(digits) == 10:
        # US number without country code: (123) 456-7890
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    else:
        # International or other format
        return phone


def is_valid_phone_number(phone: str) -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Extract digits
    digits = ''.join(filter(str.isdigit, phone))
    
    # Check length (10 digits for US, 11 with country code)
    if len(digits) < 10 or len(digits) > 15:
        return False
    
    # US numbers should start with valid area code
    if len(digits) == 10:
        area_code = digits[:3]
        # Area codes can't start with 0 or 1
        if area_code.startswith(('0', '1')):
            return False
    
    return True


async def send_twilio_sms(
    to_phone: str,
    message: str,
    from_phone: str = None
) -> dict:
    """
    Send SMS using Twilio
    
    Args:
        to_phone: Recipient phone number
        message: SMS message
        from_phone: Sender phone number (optional)
        
    Returns:
        Dict with success status and message SID
    """
    try:
        from twilio.rest import Client
        
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise Exception("Twilio credentials not configured")
        
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message_obj = client.messages.create(
            body=message,
            from_=from_phone or settings.TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        
        logger.info(
            "SMS sent successfully",
            to_phone=f"{to_phone[:3]}***",
            message_sid=message_obj.sid
        )
        
        return {
            "success": True,
            "message_sid": message_obj.sid
        }
        
    except Exception as e:
        logger.error("Failed to send SMS", error=str(e), to_phone=f"{to_phone[:3]}***")
        return {
            "success": False,
            "error": str(e)
        }