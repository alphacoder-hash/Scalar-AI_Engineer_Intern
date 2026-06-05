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
        """Handle Vapi function calls - must return correct format"""
        func = message.get("functionCall", {})
        name = func.get("name")
        
        # Parameters can be a string or dict
        params = func.get("parameters", {})
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except:
                params = {}

        try:
            if name == "check_availability":
                start_date = params.get("start_date")
                end_date = params.get("end_date")

                # Default to next 7 days if not specified
                if not start_date:
                    start_date = datetime.utcnow().isoformat()
                if not end_date:
                    end_date = (datetime.utcnow() + timedelta(days=7)).isoformat()

                slots = await self.calendar_manager.get_available_slots(start_date, end_date)

                if slots:
                    slot_list = ", ".join([s["formatted"] for s in slots[:3]])
                    result = f"Available slots: {slot_list}. Which works best for you?"
                else:
                    result = "No slots available in that range. Try a different week."

                return {"result": result}

            elif name == "book_slot":
                datetime_str = params.get("datetime")
                name_val = params.get("name")
                email = params.get("email")

                if not all([datetime_str, name_val, email]):
                    return {"result": "I need the date, your name, and email to book. Could you provide those?"}

                booking = await self.calendar_manager.book_slot(datetime_str, name_val, email)
                return {"result": booking["message"]}

            else:
                return {"result": f"Unknown function: {name}"}

        except Exception as e:
            print(f"Function call error: {e}")
            return {"result": "I had trouble with that. Let me try again - what time works for you?"}

    async def _log_call(self, report: Dict):
        """Log call metrics for evals"""
        metrics = {
            "call_id": report.get("call", {}).get("id"),
            "duration": report.get("durationSeconds"),
            "ended_reason": report.get("endedReason"),
            "success": report.get("endedReason") not in ["error", "assistant-error"],
            "timestamp": datetime.utcnow().isoformat()
        }

        log_path = Path(__file__).parent.parent / "evals" / "call_logs.jsonl"
        log_path.parent.mkdir(exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(metrics) + "\n")

        print(f"Call logged: {metrics}")
