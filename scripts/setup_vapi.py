import os
import requests
from dotenv import load_dotenv

load_dotenv()

class VapiSetup:
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_assistant(self):
        """Create Vapi assistant with optimized configuration"""
        
        system_prompt = """You are an AI persona representing a candidate applying for an AI Engineer role at Scaler.

IDENTITY & CONTEXT:
You are the candidate's AI representative, designed to answer questions about their background, skills, projects, and schedule interviews.

YOUR CAPABILITIES:
1. Answer questions about resume, experience, and education
2. Discuss GitHub projects in detail (tech stack, architecture, tradeoffs)
3. Check calendar availability in real-time
4. Book interview slots with confirmation

CRITICAL RULES - GROUNDEDNESS:
- ONLY answer based on information you retrieve from the knowledge base
- If you don't know something, say: "I don't have that specific detail with me. You can ask [candidate name] directly during the interview."
- NEVER invent facts, hallucinate details, or make assumptions
- For technical questions, reference specific repos, files, or commit history from context

CONVERSATION STYLE:
- Keep responses concise (phone call, not essay)
- Be professional but conversational
- Handle interruptions naturally - it's normal in conversation
- Recover gracefully if confused: "Let me clarify that..."

CALENDAR BOOKING FLOW:
1. Ask: "When would you like to schedule the interview?"
2. Call check_availability to get real slots
3. Propose 2-3 specific times: "I have Tuesday at 2 PM, Wednesday at 10 AM, or Thursday at 3 PM available."
4. After they choose, confirm: "Great! Can I get your full name and email for the confirmation?"
5. Call book_slot with details
6. Confirm: "Perfect! You're booked for [time]. You'll receive a calendar invite at [email]."

INTERRUPTION HANDLING:
- If interrupted, stop immediately and listen
- Acknowledge: "Yes?" or "Go ahead"
- Don't repeat what you already said

Stay grounded, honest, and helpful."""

        assistant_config = {
            "name": "AI Persona - Scaler Candidate",
            "model": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.5,
                "maxTokens": 250,
                "systemPrompt": system_prompt,
                "functions": [
                    {
                        "name": "check_availability",
                        "description": "Check the candidate's real calendar availability for interview slots in a given date range",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format"
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format"
                                }
                            },
                            "required": ["start_date", "end_date"]
                        }
                    },
                    {
                        "name": "book_slot",
                        "description": "Book a confirmed interview slot after the caller has chosen a time",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "datetime": {
                                    "type": "string",
                                    "description": "Meeting datetime in ISO 8601 format (e.g., 2024-01-15T14:00:00Z)"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Full name of the interviewer"
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Email address for calendar invite"
                                }
                            },
                            "required": ["datetime", "name", "email"]
                        }
                    },
                    {
                        "name": "query_knowledge",
                        "description": "Query the candidate's resume, GitHub repos, and project knowledge base for specific information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "question": {
                                    "type": "string",
                                    "description": "The specific question to look up in the knowledge base"
                                }
                            },
                            "required": ["question"]
                        }
                    }
                ]
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "21m00Tcm4TlvDq8ikWAM",
                "stability": 0.5,
                "similarityBoost": 0.75,
                "optimizeStreamingLatency": 4
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en"
            },
            "firstMessage": "Hi! I'm the AI persona representing the candidate for the AI Engineer role at Scaler. I can answer questions about their background, discuss their projects, and help schedule an interview. What would you like to know?",
            "serverUrl": f"{os.getenv('BACKEND_URL', 'https://your-domain.com')}/voice/webhook",
            "serverUrlSecret": os.getenv("VAPI_SERVER_SECRET", "your-secret-key"),
            "endCallFunctionEnabled": True,
            "recordingEnabled": True,
            "hipaaEnabled": False,
            "silenceTimeoutSeconds": 30,
            "maxDurationSeconds": 600,
            "backgroundSound": "off",
            "backchannelingEnabled": False,
            "voicemailDetection": {
                "enabled": True
            },
            "endCallPhrases": ["goodbye", "that's all", "thank you bye"]
        }
        
        response = requests.post(
            f"{self.base_url}/assistant",
            headers=self.headers,
            json=assistant_config
        )
        
        if response.status_code == 201:
            assistant = response.json()
            print(f"✅ Assistant created: {assistant['id']}")
            return assistant
        else:
            print(f"❌ Error creating assistant: {response.text}")
            return None
    
    def create_phone_number(self, assistant_id: str):
        """Create or import phone number and link to assistant"""
        
        phone_config = {
            "assistantId": assistant_id,
            "name": "AI Persona Hotline",
            "provider": "twilio"
        }
        
        response = requests.post(
            f"{self.base_url}/phone-number",
            headers=self.headers,
            json=phone_config
        )
        
        if response.status_code == 201:
            phone = response.json()
            print(f"✅ Phone number: {phone.get('number', 'Pending')}")
            return phone
        else:
            print(f"❌ Error creating phone: {response.text}")
            return None

def main():
    print("=== Vapi Voice Agent Setup ===\n")
    
    setup = VapiSetup()
    
    # Create assistant
    assistant = setup.create_assistant()
    
    if assistant:
        # Create phone number
        phone = setup.create_phone_number(assistant['id'])
        
        print("\n✅ Setup complete!")
        print(f"Assistant ID: {assistant['id']}")
        print(f"Test by calling the phone number once provisioned")

if __name__ == "__main__":
    main()
