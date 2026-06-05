import json
import os
import sys
from typing import Dict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, os.path.dirname(__file__))
from rag_engine_groq import RAGEngine
from calendar_calcom import CalendarManager


def _to_ist_str(dt_str: str) -> str:
    """Convert any ISO datetime string to a human-readable IST string."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        ist = dt + timedelta(hours=5, minutes=30)
        return ist.strftime("%A, %B %d at %I:%M %p IST")
    except Exception:
        return dt_str


class VoiceHandler:
    def __init__(self, rag: RAGEngine = None):
        self.calendar = CalendarManager()
        self.rag = rag if rag is not None else RAGEngine()

    async def handle_webhook(self, payload: Dict) -> Dict:
        message = payload.get("message", {})
        mtype = message.get("type", "")

        if mtype == "tool-calls":
            return await self._handle_tool_calls(message)
        if mtype == "function-call":
            return await self._handle_legacy(message)
        if mtype in ("end-of-call-report", "hang"):
            self._log_call(message)
        return {"status": "ok"}

    # ── Tool call formats ─────────────────────────────────────────────────────

    async def _handle_tool_calls(self, message: Dict) -> Dict:
        results = []
        for tc in message.get("toolCallList", []):
            tc_id = tc.get("id", "")
            func = tc.get("function", {})
            raw = func.get("arguments", {})
            params = raw if isinstance(raw, dict) else self._parse_json(raw)
            result = await self._dispatch(func.get("name", ""), params, message)
            results.append({"toolCallId": tc_id, "result": result})
        return {"results": results}

    async def _handle_legacy(self, message: Dict) -> Dict:
        func = message.get("functionCall") or message.get("function_call") or {}
        params = func.get("parameters", {})
        if isinstance(params, str):
            params = self._parse_json(params)
        result = await self._dispatch(func.get("name", ""), params, message)
        return {"result": result}

    # ── Dispatcher ────────────────────────────────────────────────────────────

    async def _dispatch(self, name: str, params: Dict, message: Dict) -> str:
        call_id = (message.get("call") or {}).get("id")
        try:
            if name == "check_availability":
                return await self._check_availability(params, call_id)
            if name == "book_slot":
                return await self._book_slot(params, call_id)
            if name == "ask_knowledge_base":
                return await self._ask_knowledge_base(params, call_id)
            self._log({"call_id": call_id, "tool": name, "ok": False, "error": "unknown_tool"})
            return "I didn't recognise that action — want me to check availability or book a slot?"
        except Exception as exc:
            self._log({"call_id": call_id, "tool": name, "ok": False, "error": str(exc)[:300]})
            return "I hit a small snag there — shall I try again?"

    # ── ask_knowledge_base ────────────────────────────────────────────────────

    async def _ask_knowledge_base(self, params: Dict, call_id) -> str:
        question = (params.get("question") or "").strip()
        if not question:
            return "Could you repeat the question?"
        try:
            # Direct in-process call — no HTTP loopback, ~150ms faster
            result = await self.rag.query(question, session_id=call_id or "voice", voice=True)
            answer = result.get("answer", "").strip()
            self._log({"call_id": call_id, "tool": "ask_knowledge_base", "ok": True})
            return answer or "I don't have that detail — Vaibhav can cover it directly in the interview."
        except Exception as exc:
            self._log({"call_id": call_id, "tool": "ask_knowledge_base",
                       "ok": False, "error": str(exc)[:200]})
            return "I had a moment of trouble there — could you repeat the question?"

    # ── check_availability ────────────────────────────────────────────────────

    async def _check_availability(self, params: Dict, call_id) -> str:
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date().isoformat()
        next7 = (now_utc.date() + timedelta(days=7)).isoformat()
        start = params.get("start_date") or today
        end   = params.get("end_date")   or next7

        slots = await self.calendar.get_available_slots(start, end)
        self._log({"call_id": call_id, "tool": "check_availability", "ok": True,
                   "slots_found": len(slots)})

        if not slots:
            return "That window looks fully booked — shall I check the following week instead?"

        # Always convert to IST for the caller (all times stored as UTC in slot["start"])
        formatted = [_to_ist_str(s["start"]) for s in slots[:3]]
        if len(formatted) == 1:
            return f"I have one slot open: {formatted[0]}. Does that work for you?"
        options = ", or ".join([", ".join(formatted[:-1]), formatted[-1]])
        return f"I have a few open slots: {options}. Which works best?"

    # ── book_slot ─────────────────────────────────────────────────────────────

    async def _book_slot(self, params: Dict, call_id) -> str:
        dt    = (params.get("datetime") or "").strip()
        name  = (params.get("name")     or "").strip()
        email = (params.get("email")    or "").strip()

        missing = []
        if not dt:    missing.append("a time slot")
        if not name:  missing.append("your full name")
        if not email: missing.append("your email address")
        if missing:
            self._log({"call_id": call_id, "tool": "book_slot", "ok": False,
                       "error": f"missing: {missing}"})
            return f"I just need {' and '.join(missing)} to lock that in — could you share those?"

        booking = await self.calendar.book_slot(dt, name, email)
        confirmed = booking.get("status") == "confirmed"
        self._log({"call_id": call_id, "tool": "book_slot", "ok": confirmed,
                   "booking_confirmed": confirmed, "source": booking.get("source")})

        if confirmed:
            ist = _to_ist_str(booking.get("start", dt))
            return (
                f"Done! You're booked for {ist}. "
                f"The calendar invite is on its way to {email} right now."
            )
        return (
            "Something went wrong with the booking \u2014 "
            "could you confirm the time and email and I'll try again?"
        )

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, metrics: Dict):
        log_path = Path(__file__).parent.parent / "evals" / "call_logs.jsonl"
        log_path.parent.mkdir(exist_ok=True)
        metrics["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics) + "\n")

    def _log_call(self, report: Dict):
        ended    = report.get("endedReason", "")
        analysis = report.get("analysis") or {}
        self._log({
            "call_id":      (report.get("call") or {}).get("id"),
            "duration":     report.get("durationSeconds"),
            "started_at":   report.get("startedAt"),
            "ended_at":     report.get("endedAt"),
            "cost":         report.get("cost"),
            "success":      ended not in {"error", "assistant-error", "pipeline-error"},
            "ended_reason": ended,
            "summary":      analysis.get("summary"),
        })

    @staticmethod
    def _parse_json(raw) -> Dict:
        try:
            return json.loads(raw) if raw else {}
        except Exception:
            return {}
