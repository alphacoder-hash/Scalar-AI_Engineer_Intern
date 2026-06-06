import sys
import re
import json
import time
import collections
import httpx
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict

load_dotenv()

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
# Share the already-loaded RAGEngine instance — avoids loading the model twice
voice_handler = VoiceHandler(rag=rag_engine)


@app.on_event("startup")
async def start_keepalive():
    """Ping /ping every 5 minutes so Railway never idles the container."""
    import asyncio
    backend_url = os.getenv("BACKEND_URL", "")
    if not backend_url:
        return
    async def _loop():
        await asyncio.sleep(60)          # wait 1 min after startup
        while True:
            try:
                async with httpx.AsyncClient(timeout=10) as cl:
                    await cl.get(f"{backend_url}/ping")
            except Exception:
                pass
            await asyncio.sleep(300)     # every 5 minutes
    asyncio.create_task(_loop())

# ── Rate limiter (10 requests / 60s per IP) ───────────────────────────────────
_RATE_WINDOW  = 60
_RATE_LIMIT   = 10
_MAX_BUCKETS  = 10_000   # cap dict size to prevent memory exhaustion
_rate_buckets: Dict[str, list] = collections.defaultdict(list)

def _check_rate(ip: str) -> bool:
    now = time.time()
    # Evict oldest IP entry when cap is hit
    if ip not in _rate_buckets and len(_rate_buckets) >= _MAX_BUCKETS:
        del _rate_buckets[next(iter(_rate_buckets))]
    _rate_buckets[ip] = [t for t in _rate_buckets[ip] if now - t < _RATE_WINDOW]
    if len(_rate_buckets[ip]) >= _RATE_LIMIT:
        return False
    _rate_buckets[ip].append(now)
    return True

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host or "unknown")

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
    """Extract datetime/name/email from a booking message via LLM.
    Uses a fresh session each time to avoid history contamination.
    Injection-checks the message first so crafted booking messages can't bypass _INJECTION_RE.
    """
    from rag_engine_groq import _INJECTION_RE, _REJECTION
    if _INJECTION_RE.search(msg):
        return "", "", ""
    extract_prompt = (
        "Extract scheduling info from the user message below. "
        "Return ONLY a JSON object with exactly these keys: "
        '"datetime" (ISO-8601 string, empty string if not specified), '
        '"name" (full name, empty string if not given), '
        '"email" (email address, empty string if not given). '
        "No other text.\n"
        f"USER_MESSAGE: {msg}"
    )
    import uuid as _uuid
    result = await rag_engine.query(extract_prompt, session_id=f"_extract_{_uuid.uuid4().hex}")
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


BOOKING_KEYWORDS = {"book", "schedule", "availability", "available",
                    "set up a call", "find a time", "interview slot", "arrange a meeting"}


def _wants_booking(text: str) -> bool:
    """Only trigger booking flow for unambiguous scheduling intent.
    Avoids intercepting 'interview at Centific', 'available skills', etc.
    """
    lower = text.lower().strip()
    # Explicit scheduling phrases
    if re.search(r"\b(book|schedule|set up|arrange)\b.{0,30}\b(interview|call|meeting|slot|time)\b", lower):
        return True
    # Very short messages that are clearly booking requests
    if len(lower) < 60 and re.search(r"\b(check (your |his )?(availability|calendar)|when (are you|is he|is vaibhav) (free|available)|interview slot)\b", lower):
        return True
    return False


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


@app.get("/ping")
async def ping():
    """Lightweight keepalive endpoint — called every 5 min to prevent Railway sleep."""
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    if not _check_rate(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests — slow down.")
    try:
        msg = (body.message or "").strip()
        if _wants_booking(msg):
            return await _handle_booking(msg, body.session_id)
        result = await rag_engine.query(body.message, session_id=body.session_id)
        return ChatResponse(
            response=result["answer"],
            session_id=result["session_id"],
            sources=result.get("sources", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    ip = websocket.client.host or "unknown"
    try:
        while True:
            data = await websocket.receive_json()
            if not _check_rate(ip):
                await websocket.send_json({"type": "error", "content": "Rate limit exceeded."})
                continue
            message    = data.get("message", "")
            session_id = data.get("session_id")

            # For booking intent over WebSocket, send a prompt to use the modal
            # (the frontend BookingModal handles the full booking flow)
            if _wants_booking(message):
                await websocket.send_json({
                    "type": "content",
                    "content": "Sure! Click the **📅 Book Interview** button at the top to pick a slot and confirm your details — it connects live to the calendar.",
                    "session_id": session_id or ""
                })
                await websocket.send_json({"type": "sources", "sources": [], "session_id": session_id or ""})
                continue

            async for chunk in rag_engine.query_stream(message, session_id):
                await websocket.send_json(chunk)
    except WebSocketDisconnect:
        pass


@app.post("/voice/query")
async def voice_query(request: Request):
    """
    Dual-mode RAG endpoint:
    1. Called directly by ask_knowledge_base tool (Vapi server URL) with Vapi tool-call payload
    2. Called internally by voice_handler with {"question": ..., "call_id": ...}
    """
    try:
        body = await request.json()

        # Mode 1: Vapi tool-call payload
        message = body.get("message", {})
        if message.get("type") == "tool-calls":
            results = []
            for tc in message.get("toolCallList", []):
                tc_id = tc.get("id", "")
                func = tc.get("function", {})
                raw = func.get("arguments", {})
                params = raw if isinstance(raw, dict) else json.loads(raw or "{}")
                question = (params.get("question") or "").strip()
                call_id = (message.get("call") or {}).get("id", "voice")
                if not question:
                    results.append({"toolCallId": tc_id, "result": "Could you repeat that?"})
                    continue
                result = await rag_engine.query(question, session_id=call_id, voice=True)
                results.append({"toolCallId": tc_id, "result": result["answer"]})
            return {"results": results}

        # Mode 2: Internal call from voice_handler
        question = (body.get("question") or "").strip()
        session_id = body.get("call_id") or "voice"
        if not question:
            return {"answer": "Could you repeat that question?"}
        result = await rag_engine.query(question, session_id=session_id, voice=True)
        return {"answer": result["answer"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


async def _dispatch_voice(request: Request) -> Dict:
    """Parse webhook body, verify Vapi HMAC signature if secret is set, then dispatch."""
    body = b""
    try:
        body = await request.body()
        payload = json.loads(body) if body else {}
    except Exception:
        payload = {}

    secret = os.getenv("VAPI_SERVER_SECRET")
    if secret:
        import hmac as _hmac, hashlib
        sig = request.headers.get("x-vapi-signature", "")
        expected = _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return await voice_handler.handle_webhook(payload)


@app.post("/voice/webhook")
async def voice_webhook(request: Request):
    try:
        return await _dispatch_voice(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Vapi also posts to /vapi/webhook on some dashboard configs — alias it
@app.post("/vapi/webhook")
async def vapi_webhook_alias(request: Request):
    try:
        return await _dispatch_voice(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
