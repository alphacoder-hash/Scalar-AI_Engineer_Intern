import os
from datetime import datetime, timedelta
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarManager:
    def __init__(self):
        self.service = None
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar"""
        creds = None
        
        # Token file stores user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                credentials_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials.json")
                if os.path.exists(credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    print("Warning: Google Calendar credentials not found")
                    return
            
            # Save credentials for next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        if creds:
            self.service = build('calendar', 'v3', credentials=creds)
    
    async def get_available_slots(
        self, 
        start_date: str, 
        end_date: str,
        duration_minutes: int = 30
    ) -> List[Dict]:
        """Get available time slots"""
        if not self.service:
            return []
        
        # Parse dates
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        # Get busy times
        body = {
            "timeMin": start.isoformat() + 'Z',
            "timeMax": end.isoformat() + 'Z',
            "items": [{"id": self.calendar_id}]
        }
        
        events_result = self.service.freebusy().query(body=body).execute()
        busy_times = events_result['calendars'][self.calendar_id]['busy']
        
        # Generate available slots (9 AM - 5 PM, weekdays)
        available_slots = []
        current = start
        
        while current < end:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue
            
            # Working hours: 9 AM - 5 PM
            slot_start = current.replace(hour=9, minute=0, second=0, microsecond=0)
            slot_end = current.replace(hour=17, minute=0, second=0, microsecond=0)
            
            while slot_start < slot_end:
                slot_finish = slot_start + timedelta(minutes=duration_minutes)
                
                # Check if slot is free
                is_free = True
                for busy in busy_times:
                    busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                    busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                    
                    if (slot_start < busy_end and slot_finish > busy_start):
                        is_free = False
                        break
                
                if is_free:
                    available_slots.append({
                        "start": slot_start.isoformat(),
                        "end": slot_finish.isoformat()
                    })
                
                slot_start = slot_finish
            
            current += timedelta(days=1)
        
        return available_slots[:20]  # Return max 20 slots
    
    async def book_slot(
        self, 
        datetime_str: str, 
        attendee_name: str, 
        attendee_email: str,
        duration_minutes: int = 30
    ) -> Dict:
        """Book a calendar slot"""
        if not self.service:
            raise Exception("Calendar service not initialized")
        
        start_time = datetime.fromisoformat(datetime_str)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        event = {
            'summary': f'Interview with {attendee_name}',
            'description': f'Screening interview booked via AI persona',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [
                {'email': attendee_email, 'displayName': attendee_name},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        event = self.service.events().insert(
            calendarId=self.calendar_id, 
            body=event,
            sendUpdates='all'
        ).execute()
        
        return {
            "id": event.get('id'),
            "link": event.get('htmlLink'),
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }
    
    def is_ready(self) -> bool:
        """Check if calendar is ready"""
        return self.service is not None
