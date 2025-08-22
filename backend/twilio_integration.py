"""
Twilio Integration Module for VoiceAI
Handles real phone calls, recordings, and transcriptions
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioException
import requests
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwilioManager:
    def __init__(self):
        # Twilio credentials (set these in environment variables)
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid_here')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token_here')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')
        self.webhook_base_url = os.getenv('WEBHOOK_BASE_URL', 'https://voiceai-backend-production-81d6.up.railway.app')
        
        # Initialize Twilio client
        try:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {str(e)}")
            self.client = None

    def create_phone_number_webhook(self, phone_number: str = None) -> Dict[str, Any]:
        """Configure webhook URLs for a Twilio phone number"""
        if not self.client:
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            phone_number = phone_number or self.phone_number
            
            # Update phone number webhook configuration
            incoming_phone_number = self.client.incoming_phone_numbers.list(
                phone_number=phone_number
            )[0]
            
            # Configure webhooks
            webhook_url = f"{self.webhook_base_url}/api/v1/twilio/voice"
            status_callback_url = f"{self.webhook_base_url}/api/v1/twilio/status"
            
            incoming_phone_number.update(
                voice_url=webhook_url,
                voice_method='POST',
                status_callback=status_callback_url,
                status_callback_method='POST'
            )
            
            return {
                "success": True,
                "phone_number": phone_number,
                "webhook_url": webhook_url,
                "status_callback_url": status_callback_url
            }
            
        except Exception as e:
            logger.error(f"Failed to configure webhook: {str(e)}")
            return {"success": False, "error": str(e)}

    def generate_voice_response(self, tenant_id: str = None) -> str:
        """Generate TwiML response for incoming calls"""
        response = VoiceResponse()
        
        # Greeting message
        greeting = """
        Hello! Thank you for calling our dental practice. 
        I'm your AI assistant and I'll help you schedule an appointment today.
        Please tell me your name, phone number, and when you'd like to come in.
        I'll be recording this call to ensure we get all your details correctly.
        Please speak after the beep.
        """
        
        response.say(greeting, voice='alice', language='en-US')
        
        # Record the call
        record_url = f"{self.webhook_base_url}/api/v1/twilio/recording"
        if tenant_id:
            record_url += f"?tenant_id={tenant_id}"
            
        response.record(
            action=record_url,
            method='POST',
            max_length=300,  # 5 minutes max
            finish_on_key='#',
            transcribe=True,
            transcribe_callback=f"{self.webhook_base_url}/api/v1/twilio/transcription"
        )
        
        return str(response)

    def get_call_details(self, call_sid: str) -> Dict[str, Any]:
        """Retrieve detailed information about a call"""
        if not self.client:
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            call = self.client.calls(call_sid).fetch()
            
            return {
                "success": True,
                "call_sid": call.sid,
                "from_number": call.from_,
                "to_number": call.to,
                "status": call.status,
                "duration": call.duration,
                "start_time": call.start_time.isoformat() if call.start_time else None,
                "end_time": call.end_time.isoformat() if call.end_time else None,
                "price": call.price,
                "price_unit": call.price_unit
            }
            
        except Exception as e:
            logger.error(f"Failed to get call details: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_call_recordings(self, call_sid: str) -> List[Dict[str, Any]]:
        """Get all recordings for a specific call"""
        if not self.client:
            return []
        
        try:
            recordings = self.client.recordings.list(call_sid=call_sid)
            
            recording_list = []
            for recording in recordings:
                recording_data = {
                    "sid": recording.sid,
                    "call_sid": recording.call_sid,
                    "duration": recording.duration,
                    "date_created": recording.date_created.isoformat() if recording.date_created else None,
                    "uri": recording.uri,
                    "channels": recording.channels,
                    "source": recording.source
                }
                
                # Get recording URL
                recording_data["url"] = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
                
                recording_list.append(recording_data)
            
            return recording_list
            
        except Exception as e:
            logger.error(f"Failed to get recordings: {str(e)}")
            return []

    def download_recording(self, recording_sid: str) -> Optional[bytes]:
        """Download recording audio file"""
        if not self.client:
            return None
        
        try:
            recording = self.client.recordings(recording_sid).fetch()
            recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"
            
            # Download the recording
            auth_header = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
            headers = {"Authorization": f"Basic {auth_header}"}
            
            response = requests.get(recording_url, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download recording: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download recording: {str(e)}")
            return None

    def get_transcription(self, transcription_sid: str) -> Optional[str]:
        """Get transcription text for a recording"""
        if not self.client:
            return None
        
        try:
            transcription = self.client.transcriptions(transcription_sid).fetch()
            return transcription.transcription_text
            
        except Exception as e:
            logger.error(f"Failed to get transcription: {str(e)}")
            return None

    def make_outbound_call(self, to_number: str, tenant_id: str = None) -> Dict[str, Any]:
        """Make an outbound call (for testing or callbacks)"""
        if not self.client:
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            # Generate TwiML for outbound call
            twiml_url = f"{self.webhook_base_url}/api/v1/twilio/outbound"
            if tenant_id:
                twiml_url += f"?tenant_id={tenant_id}"
            
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=twiml_url,
                method='POST',
                status_callback=f"{self.webhook_base_url}/api/v1/twilio/status"
            )
            
            return {
                "success": True,
                "call_sid": call.sid,
                "to_number": to_number,
                "from_number": self.phone_number,
                "status": call.status
            }
            
        except Exception as e:
            logger.error(f"Failed to make outbound call: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_phone_numbers(self) -> List[Dict[str, Any]]:
        """Get all Twilio phone numbers"""
        if not self.client:
            return []
        
        try:
            phone_numbers = self.client.incoming_phone_numbers.list()
            
            numbers_list = []
            for number in phone_numbers:
                numbers_list.append({
                    "sid": number.sid,
                    "phone_number": number.phone_number,
                    "friendly_name": number.friendly_name,
                    "capabilities": {
                        "voice": number.capabilities.get('voice', False),
                        "sms": number.capabilities.get('sms', False),
                        "mms": number.capabilities.get('mms', False)
                    },
                    "voice_url": number.voice_url,
                    "status_callback": number.status_callback
                })
            
            return numbers_list
            
        except Exception as e:
            logger.error(f"Failed to get phone numbers: {str(e)}")
            return []

    def validate_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """Validate and format phone number"""
        try:
            from twilio.rest import Client
            lookup = self.client.lookups.phone_numbers(phone_number).fetch()
            
            return {
                "success": True,
                "phone_number": lookup.phone_number,
                "country_code": lookup.country_code,
                "national_format": lookup.national_format,
                "carrier": lookup.carrier.get('name') if lookup.carrier else None
            }
            
        except Exception as e:
            logger.error(f"Failed to validate phone number: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_call_logs(self, limit: int = 50, date_from: datetime = None) -> List[Dict[str, Any]]:
        """Get recent call logs"""
        if not self.client:
            return []
        
        try:
            # Default to last 30 days
            if not date_from:
                date_from = datetime.now() - timedelta(days=30)
            
            calls = self.client.calls.list(
                start_time_after=date_from,
                limit=limit
            )
            
            call_logs = []
            for call in calls:
                call_logs.append({
                    "call_sid": call.sid,
                    "from_number": call.from_,
                    "to_number": call.to,
                    "status": call.status,
                    "duration": call.duration,
                    "start_time": call.start_time.isoformat() if call.start_time else None,
                    "end_time": call.end_time.isoformat() if call.end_time else None,
                    "direction": call.direction,
                    "price": call.price
                })
            
            return call_logs
            
        except Exception as e:
            logger.error(f"Failed to get call logs: {str(e)}")
            return []

# Global instance
twilio_manager = TwilioManager()

def get_twilio_manager() -> TwilioManager:
    """Get the global Twilio manager instance"""
    return twilio_manager