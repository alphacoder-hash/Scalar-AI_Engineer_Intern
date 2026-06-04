import os
from datetime import datetime, timedelta
from typing import List, Dict
import httpx

class CalendarManager:
    def __init__(self):
        self.api_key = os.getenv("CALCOM_API_KEY")
        self.username = os.getenv("CALCOM_USERNAME")
        self.base_url = "https://api.cal.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.event_type_id = None
        self._get_event_type()
    
    def _get_event_type(self):
        """Get the event type ID for bookings"""
        try:
            response = httpx.get(
                f"{self.base_url}/event-types",
                headers=self.headers,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                event_types = data.get("event_types", [])
                if event_types:
                    # Use first event type or create one
                    self.event_type_id = event_types[0]["id"]
                    print(f"✓ Cal.com event type: {event_types[0].get('title', 'Interview')}")
                else:
                    print("⚠ No event types found in Cal.com. Create one at cal.com/event-types")
        except Exception as e:
            print(f"⚠ Cal.com setup: {str(e)}")
    
    async def get_available_slots(
        self, 
        start_date: str, 
        end_date: str,
        duration_minutes: int = 30
    ) -> List[Dict]:
        """Get available time slots from Cal.com"""
        if not self.api_key or not self.event_type_id:
            # Return mock slots for testing
            return self._generate_mock_slots(start_date, end_date)
        
        try:
            # Cal.com availability API
            start = datetime.fromisoformat(start_date.replace('Z', ''))
            end = datetime.fromisoformat(end_date.replace('Z', ''))
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/availability",
                    headers=self.headers,
                    params={
                        "eventTypeId": self.event_type_id,
                        "startTime": start.isoformat(),
                        "endTime": end.isoformat()
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    slots = []
                    for slot in data.get("slots", [])[:20]:
                        slots.append({
                            "start": slot["time"],
                            "end": (datetime.fromisoformat(slot["time"]) + timedelta(minutes=duration_minutes)).isoformat()
                        })
                    return slots
                else:
                    return self._generate_mock_slots(start_date, end_date)
        
        except Exception as e:
            print(f"Cal.com availability error: {str(e)}")
            return self._generate_mock_slots(start_date, end_date)
    
    def _generate_mock_slots(self, start_date: str, end_date: str) -> List[Dict]:
        """Generate mock slots for testing"""
        start = datetime.fromisoformat(start_date.replace('Z', ''))
        end = datetime.fromisoformat(end_date.replace('Z', ''))
        
        slots = []
        current = start
        
        while current < end and len(slots) < 10:
            # Skip weekends
            if current.weekday() < 5:
                # 10 AM, 2 PM, 4 PM slots
                for hour in [10, 14, 16]:
                    slot_time = current.replace(hour=hour, minute=0, second=0, microsecond=0)
                    if start <= slot_time < end:
                        slots.append({
                            "start": slot_time.isoformat(),
                            "end": (slot_time + timedelta(minutes=30)).isoformat()
                        })
            
            current += timedelta(days=1)
        
        return slots[:10]
    
    async def book_slot(
        self, 
        datetime_str: str, 
        attendee_name: str, 
        attendee_email: str,
        duration_minutes: int = 30
    ) -> Dict:
        """Book a meeting slot via Cal.com"""
        if not self.api_key or not self.event_type_id:
            # Mock booking for testing
            return {
                "id": f"mock-{datetime.now().timestamp()}",
                "link": f"https://cal.com/{self.username}/mock-booking",
                "start": datetime_str,
                "end": (datetime.fromisoformat(datetime_str) + timedelta(minutes=duration_minutes)).isoformat(),
                "status": "mock"
            }
        
        try:
            start_time = datetime.fromisoformat(datetime_str.replace('Z', ''))
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/bookings",
                    headers=self.headers,
                    json={
                        "eventTypeId": self.event_type_id,
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat(),
                        "responses": {
                            "name": attendee_name,
                            "email": attendee_email,
                            "notes": f"Interview booking via AI Persona (Sam) for Vaibhav Pandey"
                        },
                        "timeZone": "UTC",
                        "language": "en",
                        "metadata": {
                            "source": "ai-persona-sam"
                        }
                    },
                    timeout=15.0
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return {
                        "id": data.get("id"),
                        "link": data.get("attendees", [{}])[0].get("bookingUrl", f"https://cal.com/{self.username}"),
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat(),
                        "status": "confirmed"
                    }
                else:
                    raise Exception(f"Cal.com API error: {response.status_code}")
        
        except Exception as e:
            print(f"Cal.com booking error: {str(e)}")
            # Return mock booking as fallback
            return {
                "id": f"mock-{datetime.now().timestamp()}",
                "link": f"https://cal.com/{self.username}",
                "start": datetime_str,
                "end": (datetime.fromisoformat(datetime_str) + timedelta(minutes=duration_minutes)).isoformat(),
                "status": "pending",
                "note": "Booking pending - Cal.com API issue"
            }
    
    def is_ready(self) -> bool:
        """Check if calendar is ready"""
        return self.api_key is not None
