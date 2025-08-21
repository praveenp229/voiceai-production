"""
Google Calendar Integration for VoiceAI 2.0
Automatically creates calendar events for scheduled appointments
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

# Mock Google Calendar integration (in production, use Google Calendar API)
class GoogleCalendarIntegrator:
    """Handles Google Calendar API integration"""
    
    def __init__(self):
        self.calendar_id = "primary"
        self.service = None  # Would be Google Calendar API service
        self.mock_events = {}  # Mock storage for demonstration
        
    def setup_credentials(self):
        """Setup Google Calendar API credentials"""
        # In production, this would:
        # 1. Load credentials from service account or OAuth
        # 2. Build the Google Calendar API service
        # 3. Authenticate with Google
        
        print("Setting up Google Calendar integration...")
        # For now, we'll simulate the setup
        return True
    
    def create_appointment_event(self, appointment_data: Dict[str, Any]) -> Optional[str]:
        """Create a calendar event for an appointment"""
        try:
            # Parse appointment details
            patient_name = appointment_data.get("name", "Unknown Patient")
            phone = appointment_data.get("phone", "No phone")
            reason = appointment_data.get("reason", "checkup")
            appointment_time = appointment_data.get("time", "10:00 AM")
            appointment_date = appointment_data.get("date", "next available")
            
            # Calculate appointment duration based on type
            duration_minutes = self.get_appointment_duration(reason)
            
            # Create event data structure
            event_data = {
                "summary": f"Dental {reason.title()} - {patient_name}",
                "description": f"Patient: {patient_name}\nPhone: {phone}\nType: {reason}\nDuration: {duration_minutes} minutes",
                "start_time": self.parse_appointment_time(appointment_date, appointment_time),
                "end_time": self.parse_appointment_time(appointment_date, appointment_time, duration_minutes),
                "attendees": [{"email": f"{patient_name.replace(' ', '').lower()}@patient.demo", "displayName": patient_name}],
                "reminders": [
                    {"method": "email", "minutes": 24 * 60},  # 24 hours
                    {"method": "sms", "minutes": 60}  # 1 hour
                ]
            }
            
            # In production, this would call Google Calendar API:
            # event = service.events().insert(calendarId=self.calendar_id, body=event_data).execute()
            
            # For now, store in mock storage
            event_id = f"event_{len(self.mock_events) + 1}"
            self.mock_events[event_id] = event_data
            
            print(f"Created calendar event: {event_data['summary']}")
            return event_id
            
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            return None
    
    def get_appointment_duration(self, appointment_type: str) -> int:
        """Get appointment duration in minutes based on type"""
        durations = {
            "cleaning": 30,
            "checkup": 45,
            "consultation": 60,
            "emergency": 30,
            "routine": 45
        }
        return durations.get(appointment_type.lower(), 45)
    
    def parse_appointment_time(self, date_str: str, time_str: str, add_minutes: int = 0) -> str:
        """Parse appointment date/time into ISO format"""
        try:
            # For demo, create a date next week
            base_date = datetime.now() + timedelta(days=7)
            
            # Parse time (simplified)
            if "AM" in time_str.upper() or "PM" in time_str.upper():
                time_parts = time_str.upper().replace("AM", "").replace("PM", "").strip()
                if ":" in time_parts:
                    hour, minute = map(int, time_parts.split(":"))
                else:
                    hour = int(time_parts)
                    minute = 0
                
                if "PM" in time_str.upper() and hour != 12:
                    hour += 12
                elif "AM" in time_str.upper() and hour == 12:
                    hour = 0
            else:
                hour, minute = 10, 0  # Default
            
            appointment_datetime = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if add_minutes:
                appointment_datetime += timedelta(minutes=add_minutes)
            
            return appointment_datetime.isoformat()
            
        except Exception as e:
            print(f"Error parsing time: {e}")
            # Return a default time
            default_time = datetime.now() + timedelta(days=7, hours=10)
            if add_minutes:
                default_time += timedelta(minutes=add_minutes)
            return default_time.isoformat()
    
    def get_available_slots(self, date: datetime) -> list:
        """Get available appointment slots for a given date"""
        # In production, this would query Google Calendar for busy times
        # and return available slots
        
        available_slots = [
            "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
            "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM", "4:00 PM", "4:30 PM"
        ]
        
        # Remove some slots to simulate busy times
        busy_slots = ["10:30 AM", "2:30 PM"]
        return [slot for slot in available_slots if slot not in busy_slots]
    
    def send_appointment_reminder(self, event_id: str, patient_phone: str) -> bool:
        """Send appointment reminder (would integrate with SMS service)"""
        try:
            if event_id in self.mock_events:
                event = self.mock_events[event_id]
                message = f"Reminder: You have a {event['summary']} appointment tomorrow. Demo Dental Practice - (555) 123-DEMO"
                
                print(f"SMS reminder sent to {patient_phone}: {message}")
                return True
            return False
        except Exception as e:
            print(f"Error sending reminder: {e}")
            return False
    
    def get_calendar_events(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get upcoming calendar events"""
        return {
            "events": list(self.mock_events.values()),
            "total": len(self.mock_events),
            "period": f"Next {days_ahead} days"
        }
    
    def update_appointment(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing appointment"""
        try:
            if event_id in self.mock_events:
                self.mock_events[event_id].update(updates)
                print(f"Updated appointment {event_id}")
                return True
            return False
        except Exception as e:
            print(f"Error updating appointment: {e}")
            return False
    
    def cancel_appointment(self, event_id: str) -> bool:
        """Cancel an appointment"""
        try:
            if event_id in self.mock_events:
                del self.mock_events[event_id]
                print(f"Cancelled appointment {event_id}")
                return True
            return False
        except Exception as e:
            print(f"Error cancelling appointment: {e}")
            return False


class AppointmentManager:
    """Enhanced appointment management with calendar integration"""
    
    def __init__(self):
        self.calendar = GoogleCalendarIntegrator()
        self.calendar.setup_credentials()
    
    def create_appointment_with_calendar(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create appointment and sync with calendar"""
        
        # Create calendar event
        event_id = self.calendar.create_appointment_event(appointment_data)
        
        # Enhanced appointment data
        enhanced_appointment = {
            **appointment_data,
            "calendar_event_id": event_id,
            "created_at": datetime.now().isoformat(),
            "status": "confirmed",
            "reminders_sent": [],
            "notes": f"Scheduled via VoiceAI for {appointment_data.get('reason', 'checkup')}"
        }
        
        # Schedule automatic reminder (would be done via background task in production)
        if event_id and appointment_data.get("phone"):
            print(f"Reminder scheduled for {appointment_data.get('phone')}")
        
        return enhanced_appointment
    
    def get_availability_from_calendar(self, requested_date: str = None) -> Dict[str, Any]:
        """Get real availability from calendar"""
        if requested_date:
            try:
                date_obj = datetime.strptime(requested_date, "%Y-%m-%d")
            except:
                date_obj = datetime.now() + timedelta(days=1)
        else:
            date_obj = datetime.now() + timedelta(days=1)
        
        available_slots = self.calendar.get_available_slots(date_obj)
        
        return {
            "date": date_obj.strftime("%Y-%m-%d"),
            "available_slots": available_slots,
            "total_slots": len(available_slots)
        }
    
    def suggest_alternative_times(self, preferred_date: str = None) -> list:
        """Suggest alternative appointment times"""
        alternatives = []
        
        # Check next 7 days for availability
        for days_ahead in range(1, 8):
            check_date = datetime.now() + timedelta(days=days_ahead)
            availability = self.get_availability_from_calendar(check_date.strftime("%Y-%m-%d"))
            
            if availability["available_slots"]:
                alternatives.append({
                    "date": check_date.strftime("%A, %B %d"),
                    "slots": availability["available_slots"][:3]  # First 3 slots
                })
        
        return alternatives[:3]  # Return first 3 days with availability


# Example usage and testing functions
def test_calendar_integration():
    """Test the calendar integration functionality"""
    
    print("=" * 60)
    print("Testing Google Calendar Integration")
    print("=" * 60)
    
    # Create appointment manager
    manager = AppointmentManager()
    
    # Test appointment data
    test_appointment = {
        "name": "Jane Doe",
        "phone": "555-987-6543",
        "reason": "cleaning",
        "time": "2:00 PM",
        "date": "2024-01-15"
    }
    
    # Create appointment with calendar sync
    print("\n1. Creating appointment with calendar sync...")
    enhanced_appointment = manager.create_appointment_with_calendar(test_appointment)
    print(f"   Appointment created: {enhanced_appointment['name']}")
    print(f"   Calendar Event ID: {enhanced_appointment.get('calendar_event_id')}")
    
    # Check availability
    print("\n2. Checking calendar availability...")
    availability = manager.get_availability_from_calendar()
    print(f"   Available slots: {availability['available_slots']}")
    
    # Get alternative times
    print("\n3. Getting alternative appointment times...")
    alternatives = manager.suggest_alternative_times()
    for i, alt in enumerate(alternatives):
        print(f"   Option {i+1}: {alt['date']} - {', '.join(alt['slots'])}")
    
    # Get calendar events
    print("\n4. Checking calendar events...")
    events = manager.calendar.get_calendar_events()
    print(f"   Total events: {events['total']}")
    
    print("\n" + "=" * 60)
    print("Calendar Integration Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_calendar_integration()