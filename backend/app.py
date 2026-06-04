import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

load_dotenv()

# Import our modules
import sys
sys.path.insert(0, os.path.dirname(__file__))

from rag_engine_groq import RAGEngine
from calendar_calcom import CalendarManager
from voice_handler import VoiceHandler

app = FastAPI(title="Sam - AI Persona for Vaibhav Pandey", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
rag_engine = RAGEngine()
calendar_manager = CalendarManager()
voice_handler = VoiceHandler()

# ── Request Models ───────────────────────────────────────────────────────────

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

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    import os
    from pathlib import Path
    cwd = os.getcwd()
    chroma_exists = Path("chroma_db").exists()
    chroma_abs = Path("chroma_db").absolute()
    return {
        "status": "healthy",
        "candidate": os.getenv("CANDIDATE_NAME", "Vaibhav Pandey"),
        "persona": "Sam",
        "rag_ready": rag_engine.is_ready(),
        "calendar_ready": calendar_manager.is_ready(),
        "cwd": cwd,
        "chroma_exists": chroma_exists,
        "chroma_path": str(chroma_abs)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await rag_engine.query(
            request.message,
            session_id=request.session_id
        )
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
            message = data.get("message")
            session_id = data.get("session_id")
            
            async for chunk in rag_engine.query_stream(message, session_id):
                await websocket.send_json(chunk)
    except WebSocketDisconnect:
        pass

@app.post("/availability")
async def get_availability(request: AvailabilityRequest):
    try:
        slots = await calendar_manager.get_available_slots(
            request.start_date,
            request.end_date
        )
        return {"slots": slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/book")
async def book_meeting(request: BookingRequest):
    try:
        booking = await calendar_manager.book_slot(
            request.datetime,
            request.name,
            request.email
        )
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
