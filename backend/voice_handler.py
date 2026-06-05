import os
import json
from typing import Dict
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from rag_engine_groq import RAGEngine
from calendar_calcom import CalendarManager

class VoiceHandler:
    def __init__(self):
        self.rag_engine = RAGEngine()
        self.calendar_manager = CalendarManager()

    async def handle_webhook(self, payload: Dict) -> Dict:
        """Handle all Vapi webhook events"""
        message = payload.get("message", {})
        message_type = message.get("type")

        if message_type == "function-call":
            return await self._handle_function_call(message)

        elif message_type == "end-of-call-report":
            await self._log_call(message)
            return {"status": "ok"}


        return {"status": "ok"}

    async def _handle_function_call(self, message: Dict) -> Dict:
        """Handle Vapi function calls.

        Tool-call schema is driven by scripts/setup_vapi.py.
        We return a plain {"result": "..."} payload so Vapi can speak it.
        """
        func = message.get("functionCall") or message.get("function_call") or {}
        name = func.get("name")

        params = func.get("parameters", {})
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = {}

        call_ts = datetime.utcnow().isoformat()
        tool_name = name or "unknown"
        first_token_ts = (message.get("call") or {}).get("firstTokenTimestamp")


        try:
            if name == "check_availability":
                start_date = params.get("start_date")
                end_date = params.get("end_date")

                # Default to next 7 days if not specified
                if not start_date:
                    start_date = datetime.utcnow().date().isoformat()
                if not end_date:
                    end_date = (datetime.utcnow().date() + timedelta(days=7)).isoformat()

                slots = await self.calendar_manager.get_available_slots(start_date, end_date)

                if slots:
                    slot_list = ", ".join([s["formatted"] for s in slots[:3] if s.get("formatted")])
                    result = f"Available slots: {slot_list}. Which works best for you?"
                else:
                    result = "No slots available in that range. Try a different week."

                # Log tool call
                self._append_call_log({
                    "timestamp": call_ts,
                    "call_id": (message.get("call") or {}).get("id"),
                    "latency": None,
                    "duration": None,
                    "success": False,
                    "tool_call": tool_name,
                    "tool_ok": True,
                    "booking_confirmed": False
                })
                return {"result": result}


            if name == "book_slot":
                datetime_str = params.get("datetime")
                name_val = params.get("name")
                email = params.get("email")

                if not all([datetime_str, name_val, email]):
                    self._append_call_log({
                        "timestamp": call_ts,
                        "call_id": (message.get("call") or {}).get("id"),
                        "latency": None,
                        "duration": None,
                        "success": False,
                        "tool_call": tool_name,
                        "tool_ok": False,
                        "booking_confirmed": False,
                        "error": "missing_fields"
                    })
                    return {"result": "I need the date, your full name, and email to book. Could you provide those?"}


                booking = await self.calendar_manager.book_slot(datetime_str, name_val, email)
                confirmed = (booking.get("status") == "confirmed")
                source = booking.get("source")

                self._append_call_log({
                    "timestamp": call_ts,
                    "call_id": (message.get("call") or {}).get("id"),
                    "tool_call": tool_name,
                    "tool_ok": confirmed,
                    "booking_confirmed": confirmed,
                    "booking_source": source
                })
                return {"result": booking.get("message", "Confirmed! Your interview has been booked.")}

            # Unknown tool
            self._append_call_log({
                "timestamp": call_ts,
                "call_id": (message.get("call") or {}).get("id"),
                "latency": None,
                "duration": None,
                "success": False,
                "tool_call": tool_name,
                "tool_ok": False,
                "booking_confirmed": False,
                "error": "unknown_tool"
            })

            return {"result": f"Unknown function: {name}"}


        except Exception as e:
            print(f"Function call error: {e}")
            self._append_call_log({
                "timestamp": call_ts,
                "call_id": (message.get("call") or {}).get("id"),
                "tool_call": tool_name,
                "tool_ok": False,
                "booking_confirmed": False,
                "error": str(e)[:300]
            })
            return {"result": "I had trouble with that. Let me try again—what time works for you?"}

    def _append_call_log(self, metrics: Dict):
        """Append a single JSON line to eval logs."""
        log_path = Path(__file__).parent.parent / "evals" / "call_logs.jsonl"
        log_path.parent.mkdir(exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics) + "\n")


    async def _log_call(self, report: Dict):
        """Log end-of-call metrics for evals.

        eval_system.py reads: latency, duration, success.
        """
        ended_reason = report.get("endedReason", "")
        metrics = {
            "call_id": (report.get("call") or {}).get("id"),
            "latency": report.get("firstTokenLatencySeconds") or report.get("latency"),
            "duration": report.get("durationSeconds"),
            "success": ended_reason not in ["error", "assistant-error", "pipeline-error"],
            "ended_reason": ended_reason,
            "tool_call": None,
            "tool_ok": None,
            "booking_confirmed": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        log_path = Path(__file__).parent.parent / "evals" / "call_logs.jsonl"
        log_path.parent.mkdir(exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics) + "\n")
        print(f"Call logged: {metrics}")
