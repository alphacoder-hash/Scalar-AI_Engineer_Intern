import json
from typing import Dict, List
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from calendar_calcom import CalendarManager


class VoiceHandler:
    def __init__(self):
        self.calendar_manager = CalendarManager()

    async def handle_webhook(self, payload: Dict) -> Dict:
        """
        Route Vapi webhook events.

        Tool invocations arrive as message.type == "tool-calls"
        (toolCallList) or the legacy "function-call" shape.
        """
        message = payload.get("message", {})
        mtype = message.get("type", "")

        if mtype == "tool-calls":
            return await self._handle_tool_calls(message)

        if mtype == "function-call":
            return await self._handle_legacy_function_call(message)

        if mtype == "end-of-call-report":
            self._log_end_of_call(message)

        return {"status": "ok"}

    # ── New Vapi format ───────────────────────────────────────────────────────

    async def _handle_tool_calls(self, message: Dict) -> Dict:
        results = []
        for tc in message.get("toolCallList", []):
            tc_id = tc.get("id", "")
            func = tc.get("function", {})
            name = func.get("name", "")
            raw = func.get("arguments", {})
            params = raw if isinstance(raw, dict) else self._parse_json(raw)
            result = await self._dispatch(name, params, message)
            results.append({"toolCallId": tc_id, "result": result})
        return {"results": results}

    # ── Legacy format ─────────────────────────────────────────────────────────

    async def _handle_legacy_function_call(self, message: Dict) -> Dict:
        func = message.get("functionCall") or message.get("function_call") or {}
        name = func.get("name", "")
        params = func.get("parameters", {})
        if isinstance(params, str):
            params = self._parse_json(params)
        result = await self._dispatch(name, params, message)
        return {"result": result}

    # ── Dispatcher ────────────────────────────────────────────────────────────

    async def _dispatch(self, name: str, params: Dict, message: Dict) -> str:
        call_id = (message.get("call") or {}).get("id")
        try:
            if name == "check_availability":
                start = params.get("start_date") or datetime.utcnow().date().isoformat()
                end = params.get("end_date") or (datetime.utcnow().date() + timedelta(days=7)).isoformat()
                slots = await self.calendar_manager.get_available_slots(start, end)
                if slots:
                    slot_list = ", ".join(s["formatted"] for s in slots[:3] if s.get("formatted"))
                    result = f"Available slots: {slot_list}. Which works best for you?"
                else:
                    result = "No slots available in that range. Try a different week."
                self._log({"call_id": call_id, "tool": name, "ok": True, "booking_confirmed": False})
                return result

            if name == "book_slot":
                dt = params.get("datetime")
                attendee = params.get("name")
                email = params.get("email")
                if not all([dt, attendee, email]):
                    self._log({"call_id": call_id, "tool": name, "ok": False, "error": "missing_fields"})
                    return "I need the date, your full name, and email to book. Could you provide those?"
                booking = await self.calendar_manager.book_slot(dt, attendee, email)
                confirmed = booking.get("status") == "confirmed"
                self._log({"call_id": call_id, "tool": name, "ok": confirmed,
                           "booking_confirmed": confirmed, "source": booking.get("source")})
                return booking.get("message", "Confirmed! Your interview has been booked.")

            self._log({"call_id": call_id, "tool": name, "ok": False, "error": "unknown_tool"})
            return f"Unknown function: {name}"

        except Exception as exc:
            self._log({"call_id": call_id, "tool": name, "ok": False, "error": str(exc)[:300]})
            return "I had a small hiccup there — what time works for you?"

    # ── Logging helpers ───────────────────────────────────────────────────────

    def _log(self, metrics: Dict):
        log_path = Path(__file__).parent.parent / "evals" / "call_logs.jsonl"
        log_path.parent.mkdir(exist_ok=True)
        metrics["timestamp"] = datetime.utcnow().isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics) + "\n")

    def _log_end_of_call(self, report: Dict):
        ended = report.get("endedReason", "")
        self._log({
            "call_id": (report.get("call") or {}).get("id"),
            "latency": report.get("firstTokenLatencySeconds") or report.get("latency"),
            "duration": report.get("durationSeconds"),
            "success": ended not in {"error", "assistant-error", "pipeline-error"},
            "ended_reason": ended,
        })

    @staticmethod
    def _parse_json(raw) -> Dict:
        try:
            return json.loads(raw) if raw else {}
        except Exception:
            return {}
