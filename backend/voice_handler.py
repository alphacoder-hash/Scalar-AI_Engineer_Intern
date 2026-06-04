import os
from typing import Dict, Optional
from datetime import datetime, timedelta
import hmac
import hashlib
from rag_engine_groq import RAGEngine
from calendar_calcom import CalendarManager

class VoiceHandler:
    def __init__(self):
        self.rag_engine = RAGEngine()
        self.calendar_manager = CalendarManager()
        self.server_secret = os.getenv("VAPI_SERVER_SECRET", "your-secret-key")
    
    def verify_signature(self, payload: str, signature: str) -> bool:
        """Verify Vapi webhook signature"""
        expected = hmac.new(
            self.server_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    async def handle_webhook(self, payload: Dict) -> Dict:
        """Handle Vapi webhook events"""
        message_type = payload.get("message", {}).get("type")
        
        if message_type == "function-call":
            return await self._handle_function_call(payload)
        
        elif message_type == "status-update":
            status = payload.get("message", {}).get("status")
            print(f"Call status: {status}")
            return {"status": "received"}
        
        elif message_type == "transcript":
            # Log transcript for evals
            transcript = payload.get("message", {}).get("transcript")
            print(f"Transcript: {transcript}")
            return {"status": "received"}
        
        elif message_type == "end-of-call-report":
            # Log call metrics
            report = payload.get("message")
            print(f"Call ended. Duration: {report.get('duration')}s")
            return {"status": "received"}
        
        return {"status": "ok"}
    
    async def _handle_function_call(self, payload: Dict) -> Dict:
        """Handle function calls from Vapi"""
        function_call = payload.get("message", {}).get("functionCall", {})
        function_name = function_call.get("name")
        parameters = function_call.get("parameters", {})
        
        try:
            if function_name == "check_availability":
                start_date = parameters.get("start_date")
                end_date = parameters.get("end_date")
                
                # Parse dates and add buffer if needed
                if not end_date:
                    start = datetime.fromisoformat(start_date)
                    end = start + timedelta(days=7)
                    end_date = end.isoformat()
                
                slots = await self.calendar_manager.get_available_slots(
                    start_date,
                    end_date
                )
                
                # Format for voice readability
                formatted_slots = []
                for slot in slots[:5]:
                    dt = datetime.fromisoformat(slot["start"])
                    formatted = dt.strftime("%A, %B %d at %I:%M %p")
                    formatted_slots.append({
                        "datetime": slot["start"],
                        "formatted": formatted
                    })
                
                return {
                    "result": {
                        "available": len(formatted_slots) > 0,
                        "slots": formatted_slots,
                        "message": f"Found {len(formatted_slots)} available slots" if formatted_slots else "No slots available in that range"
                    }
                }
            
            elif function_name == "book_slot":
                booking = await self.calendar_manager.book_slot(
                    parameters.get("datetime"),
                    parameters.get("name"),
                    parameters.get("email")
                )
                
                dt = datetime.fromisoformat(parameters.get("datetime"))
                formatted_time = dt.strftime("%A, %B %d at %I:%M %p")
                
                return {
                    "result": {
                        "success": True,
                        "booking_id": booking["id"],
                        "time": formatted_time,
                        "message": f"Interview booked for {formatted_time}. Calendar invite sent to {parameters.get('email')}"
                    }
                }
            
            elif function_name == "query_knowledge":
                question = parameters.get("question")
                
                # Query RAG engine
                result = await self.rag_engine.query(question)
                
                return {
                    "result": {
                        "answer": result["answer"],
                        "has_info": bool(result.get("sources"))
                    }
                }
            
            else:
                return {
                    "error": f"Unknown function: {function_name}"
                }
        
        except Exception as e:
            print(f"Error in function call: {str(e)}")
            return {
                "error": f"Error: {str(e)}"
            }
    
    async def log_call_metrics(self, call_data: Dict):
        """Log call metrics for evaluation"""
        # Extract metrics
        metrics = {
            "call_id": call_data.get("id"),
            "duration": call_data.get("duration"),
            "latency": call_data.get("latency"),
            "interruptions": call_data.get("interruptions", 0),
            "success": call_data.get("endedReason") != "error"
        }
        
        # Save to file for evals
        import json
        log_file = "./evals/call_logs.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(metrics) + "\n")
        
        print(f"Logged call metrics: {metrics}")
