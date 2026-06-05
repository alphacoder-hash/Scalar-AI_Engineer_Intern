import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import re
import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(__file__))

from rag_engine_groq import RAGEngine
from calendar_calcom import CalendarManager
from voice_handler import VoiceHandler

app = FastAPI(title="Sam - AI Persona for Vaibhav Pandey", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine = RAGEngine()
calendar_manager = CalendarManager()
voice_handler = VoiceHandler()

# ── Request Models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: Optional[List[dict]] = None

class AvailabilityRequest(BaseModel):
    start_date: str
    end_date: str

class BookingRequest(BaseModel):
    datetime: str
    name: str
    email: str

# ── Helpers ───────────────────────────────────────────────────────────────────

def _log_chat_booking(session_id, dt, name, email, booking):
    log_path = Path("./evals/chat_bookings.jsonl")
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "requested_dt": dt,
            "name": name,
            "email": email,
            "status": booking.get("status"),
            "source": booking.get("source"),
            "success": booking.get("status") == "confirmed"
        }) + "\n")


async def _extract_booking_fields(msg: str):
    """Use LLM to extract datetime/name/email from a free-text message."""
    extract_prompt = (
        "Extract scheduling info from the user message below. "
        "Return ONLY a JSON object with exactly these keys: "
        '"datetime" (ISO-8601 string, empty string if not specified), '
        '"name" (full name, empty string if not given), '
        '"email" (email address, empty string if not given). '
        "No other text.\n"
        f"USER_MESSAGE: {msg}"
    )
    result = await rag_engine.query(extract_prompt, session_id="_extract")
    raw = result.get("answer", "")
    m = re.search(r"\{.*?\}", raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            return (
                (data.get("datetime") or "").strip(),
                (data.get("name") or "").strip(),
                (data.get("email") or "").strip(),
            )
        except Exception:
            pass
    return "", "", ""


BOOKING_KEYWORDS = {"book", "schedule", "availability", "available", "interview", "set up", "arrange", "slot", "meeting"}


def _wants_booking(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in BOOKING_KEYWORDS)


async def _handle_booking(msg: str, session_id: Optional[str]):
    """Full autonomous booking logic. Returns ChatResponse or None."""
    dt, name_val, email_val = await _extract_booking_fields(msg)

    # All three present → book immediately
    if dt and name_val and email_val:
        booking = await calendar_manager.book_slot(dt, name_val, email_val)
        _log_chat_booking(session_id, dt, name_val, email_val, booking)
        return ChatResponse(
            response=booking.get("message", "Done!"),
            session_id=session_id or "",
            sources=[]
        )

    # Partial info → show slots and ask for what's missing
    start = datetime.utcnow().date().isoformat()
    end = (datetime.utcnow() + timedelta(days=7)).date().isoformat()
    slots = await calendar_manager.get_available_slots(start, end)
    slot_lines = "\n".join(
        [f"  {i+1}. {s.get('formatted', s.get('start'))}" for i, s in enumerate(slots)]
    )
    missing = []
    if not dt:
        missing.append("a time from the list above (or any specific date/time)")
    if not name_val:
        missing.append("your full name")
    if not email_val:
        missing.append("your email")
    response = (
        "Happy to schedule that! Here are the next available slots (UTC):\n"
        f"{slot_lines}\n\n"
        f"Please reply with {', and '.join(missing)}."
    )
    return ChatResponse(response=response, session_id=session_id or "", sources=[])

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    chroma_path = Path("chroma_db").absolute()
    return {
        "status": "healthy",
        "candidate": os.getenv("CANDIDATE_NAME", "Vaibhav Pandey"),
        "persona": "Sam",
        "rag_ready": rag_engine.is_ready(),
        "calendar_ready": calendar_manager.is_ready(),
        "cwd": os.getcwd(),
        "chroma_exists": chroma_path.exists(),
        "chroma_path": str(chroma_path)
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        msg = (request.message or "").strip()

        if _wants_booking(msg):
            return await _handle_booking(msg, request.session_id)

        result = await rag_engine.query(request.message, session_id=request.session_id)
        return ChatResponse(
            response=result["answer"],
            session_id=result["session_id"],
            sources=result.get("sources", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id")

            if _wants_booking(message):
                booking_resp = await _handle_booking(message, session_id)
                await websocket.send_json({"type": "content", "content": booking_resp.response, "session_id": booking_resp.session_id})
                await websocket.send_json({"type": "sources", "sources": [], "session_id": booking_resp.session_id})
                continue

            async for chunk in rag_engine.query_stream(message, session_id):
                await websocket.send_json(chunk)
    except WebSocketDisconnect:
        pass


@app.post("/availability")
async def get_availability(request: AvailabilityRequest):
    try:
        slots = await calendar_manager.get_available_slots(request.start_date, request.end_date)
        return {"slots": slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/book")
async def book_meeting(request: BookingRequest):
    try:
        booking = await calendar_manager.book_slot(request.datetime, request.name, request.email)
        return {"success": True, "booking": booking}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/webhook")
async def voice_webhook(request: Request):
    try:
        payload = await request.json()
        response = await voice_handler.handle_webhook(payload)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
