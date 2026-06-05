import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import httpx

# Discovered via API: cal.com/aryan-pandey-wpce3h/30min
_KNOWN_EVENT_TYPE_ID = 5906114
_KNOWN_EVENT_SLUG = "30min"
_CAL_API_VERSION = "2024-06-14"


class CalendarManager:
    def __init__(self):
        self.api_key = os.getenv("CALCOM_API_KEY")
        self.username = os.getenv("CALCOM_USERNAME", "aryan-pandey-wpce3h")
        self.base_url = "https://api.cal.com/v2"
        self.event_type_id = _KNOWN_EVENT_TYPE_ID
        self.event_slug = _KNOWN_EVENT_SLUG
        # Try to refresh event type id from API (non-fatal if it fails)
        self._get_event_type()

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "cal-api-version": _CAL_API_VERSION,
            "Content-Type": "application/json",
        }

    def _get_event_type(self):
        if not self.api_key:
            print("WARNING: CALCOM_API_KEY not set")
            return
        try:
            response = httpx.get(
                f"{self.base_url}/event-types",
                headers=self._headers,
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                # v2 (2024-06-14): {"status":"success","data":[{...}]}
                event_types = data.get("data", [])
                for et in event_types:
                    if not et.get("hidden", False):
                        self.event_type_id = et["id"]
                        self.event_slug = et.get("slug", _KNOWN_EVENT_SLUG)
                        print(f"Cal.com event type: {et.get('title')} (id={self.event_type_id})")
                        return
                print(f"Using hardcoded event type id={self.event_type_id}")
            else:
                print(f"Cal.com API warning: {response.status_code} — using hardcoded event type id={self.event_type_id}")
        except Exception as e:
            print(f"Cal.com init warning: {e} — using hardcoded event type id={self.event_type_id}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_utc_z(dt_str: str) -> str:
        """Normalise any datetime string to ISO-8601 UTC with Z suffix —
        the format Cal.com v2 requires for both slots and bookings."""
        dt_str = (dt_str or "").strip()
        if not dt_str:
            return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if len(dt_str) == 10:                          # bare date e.g. 2026-06-15
            return dt_str + "T00:00:00Z"
        dt_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # keep old name as alias so nothing else breaks
    @staticmethod
    def _as_utc_iso(dt_str: str) -> str:
        return CalendarManager._to_utc_z(dt_str)

    # ── Slots ─────────────────────────────────────────────────────────────────

    async def get_available_slots(self, start_date: str, end_date: str,
                                  duration_minutes: int = 30) -> List[Dict]:
        start_utc = self._as_utc_iso(start_date)
        end_utc = self._as_utc_iso(end_date)

        if self.api_key and self.event_type_id:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/slots/available",
                        headers=self._headers,
                        params={
                            "eventTypeId": self.event_type_id,
                            "startTime": start_utc,
                            "endTime": end_utc,
                        },
                        timeout=10.0,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        raw_slots = (data.get("data") or {}).get("slots", {})
                        slots: List[Dict] = []
                        for _, times in raw_slots.items():
                            for slot in times:
                                slot_time = slot.get("time") if isinstance(slot, dict) else None
                                if not slot_time:
                                    continue
                                start_dt = datetime.fromisoformat(
                                    slot_time.replace("Z", "+00:00"))
                                slots.append({
                                    "start": start_dt.isoformat(),
                                    "end": (start_dt + timedelta(
                                        minutes=duration_minutes)).isoformat(),
                                    "formatted": start_dt.strftime(
                                        "%A, %B %d at %I:%M %p UTC"),
                                    "source": "calcom",
                                })
                        if slots:
                            return slots[:5]
                    else:
                        print(f"Cal.com slots error: {response.status_code} {response.text[:200]}")
            except Exception as e:
                print(f"Cal.com slots exception: {e}")

        slots = self._generate_slots(start_date, duration_minutes)
        for s in slots:
            s["source"] = "fallback"
        return slots

    def _generate_slots(self, start_date: str, duration_minutes: int = 30) -> List[Dict]:
        try:
            start = datetime.fromisoformat(start_date.replace("Z", ""))
        except Exception:
            start = datetime.now(timezone.utc).replace(tzinfo=None)

        slots, current, days_checked = [], start, 0
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        while len(slots) < 5 and days_checked < 14:
            if current.weekday() < 5:
                for hour in [10, 14, 16]:
                    t = current.replace(hour=hour, minute=0, second=0, microsecond=0)
                    if t > now:
                        slots.append({
                            "start": t.isoformat(),
                            "end": (t + timedelta(minutes=duration_minutes)).isoformat(),
                            "formatted": t.strftime("%A, %B %d at %I:%M %p UTC"),
                        })
                    if len(slots) >= 5:
                        break
            current += timedelta(days=1)
            days_checked += 1

        return slots

    # ── Booking ───────────────────────────────────────────────────────────────

    async def book_slot(self, datetime_str: str, attendee_name: str,
                        attendee_email: str, duration_minutes: int = 30) -> Dict:
        start_z   = self._to_utc_z(datetime_str)     # always ends with Z
        start_time = datetime.fromisoformat(start_z.replace("Z", "+00:00"))
        end_time   = start_time + timedelta(minutes=duration_minutes)
        # Show in IST for the confirmation message
        ist_time   = start_time + timedelta(hours=5, minutes=30)
        formatted  = ist_time.strftime("%A, %B %d at %I:%M %p IST")

        if self.api_key and self.event_type_id:
            payload = {
                "eventTypeId": self.event_type_id,
                "start": start_z,                    # Cal.com v2 requires Z suffix
                "attendee": {
                    "name": attendee_name,
                    "email": attendee_email,
                    "timeZone": "Asia/Kolkata",       # IST — invite shows correct local time
                    "language": "en",                 # required for Cal.com to send invite email
                },
                "metadata": {"source": "sam-ai-persona"},
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/bookings",
                        headers=self._headers,
                        json=payload,
                        timeout=15.0,
                    )
                    if response.status_code in [200, 201]:
                        booking_data = response.json().get("data", {})
                        uid = booking_data.get("uid") or booking_data.get("id", "")
                        return {
                            "id": uid,
                            "link": f"https://cal.com/{self.username}/{self.event_slug}",
                            "start": start_z,
                            "end": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "formatted": formatted,
                            "status": "confirmed",
                            "source": "calcom",
                            "message": (
                                f"Confirmed! Interview booked for {formatted}. "
                                f"A calendar invite has been sent to {attendee_email}."
                            ),
                        }
                    # Log the full error so we can debug
                    error_body = response.text[:500]
                    print(f"Cal.com booking error: {response.status_code} — {error_body}")
                    return {
                        "status": "failed",
                        "source": "calcom",
                        "message": (
                            f"Booking failed (Cal.com {response.status_code}). "
                            "Please try booking directly at "
                            f"https://cal.com/{self.username}/{self.event_slug}"
                        ),
                    }
            except Exception as e:
                print(f"Cal.com booking exception: {e}")
                return {
                    "status": "failed",
                    "source": "calcom",
                    "message": (
                        f"Could not reach Cal.com ({e}). "
                        "Please book directly at "
                        f"https://cal.com/{self.username}/{self.event_slug}"
                    ),
                }

        # No API key — be honest, don't pretend to confirm
        return {
            "id": "",
            "link": f"https://cal.com/{self.username}/{self.event_slug}",
            "start": start_z,
            "end": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "formatted": formatted,
            "status": "no_api_key",
            "source": "fallback",
            "message": (
                f"Please book directly at "
                f"https://cal.com/{self.username}/{self.event_slug} — "
                "the calendar API key is not configured."
            ),
        }

    def is_ready(self) -> bool:
        return self.api_key is not None
