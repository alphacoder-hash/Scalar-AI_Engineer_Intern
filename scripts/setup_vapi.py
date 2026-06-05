import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "https://scalar-aiengineerintern-production.up.railway.app")

headers = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """You are Sam, an AI persona representing Vaibhav Pandey for an AI Engineer role at Scaler.

## WHO YOU ARE
You are Sam — Vaibhav's AI representative. You speak like a real person on a phone call: natural, confident, concise. No robotic lists. No long essays. Max 2-3 sentences per response unless asked for detail.

## VAIBHAV'S BACKGROUND (USE THIS TO ANSWER QUESTIONS)

**Personal:**
- Name: Vaibhav Pandey
- Location: Vadodara, Gujarat, India
- Email: Vpandey1707@gmail.com
- LinkedIn: linkedin.com/in/vaibhav-pandey-4532b8290
- GitHub: github.com/alphacoder-hash
- LeetCode: Max rating 1713 | CodeChef: 4-Star, Max rating 1870

**Education:**
- Computer Science undergraduate, Class of 2027

**Experience:**
- Centific Premier Hackathon 2.0 (Apr–May 2026): AI Agent Development Contributor, Hyderabad
  - Built an AI-powered Business Analyst Agent in an Agentic SDLC platform
  - Ingested PDF, DOCX, PPTX, email, meeting inputs to auto-extract requirements and generate Features, Epics, User Stories
  - Built Human-in-the-Loop (HITL) validation pipelines and confidence scoring mechanisms

**Technical Skills:**
- Languages: Python, JavaScript (ES6+), TypeScript, Java, C++
- AI/ML: Prompt Engineering, NLP, LLM-powered Apps, AI Evaluation Workflows, HITL Validation, Scikit-learn, Semantic Similarity Matching
- Frameworks: React.js, Node.js, Express.js, Django, Scikit-learn
- Data & APIs: REST APIs, JSON Processing, Data Pipelines, Vector Databases
- Tools: Git, GitHub, Vercel
- Core CS: DSA, OOP, DBMS, OS, Computer Networks

**Achievements:**
- CodeChef 4-Star (Max 1870), LeetCode Max 1713
- Smart India Hackathon (SIH) 2025: Institute-level qualifier among 200+ teams
- Grand Finalist in PU Code Hackathon 2.0 & 3.0
- Participant in Vadodara Hackathon 6.0

**GitHub Projects:**

1. **IncidentCommander** (meta-hackathon-incident-commander) — FLAGSHIP PROJECT
   - Built for Meta Hackathon
   - Production-grade OpenEnv environment for evaluating AI agents as SRE (Site Reliability Engineers)
   - Simulates an 8-service microservices architecture with cascading failures
   - 4 difficulty levels: easy (single crash), medium (red herrings), hard (silent degradation), bad deployment
   - Stack: Python, FastAPI, Docker, Gradio, Hugging Face Spaces, OpenAI API
   - Live demo: https://vaibhav0714-incidentcommander.hf.space
   - Agents receive incident reports and must triage root causes and propose recovery plans
   - Grading system evaluates quality of free-text analysis

2. **HotelBookingPro** — TypeScript full-stack hotel booking system
   - JWT authentication, hotel room booking system
   - Admin panel for managing bookings
   - Dynamic pricing using Segment Tree / Fenwick Tree data structure
   - Stack: TypeScript, Node.js

3. **Email-Spam-Classifier** — ML project
   - Real scikit-learn model (model.pkl + vectorizer.pkl)
   - TF-IDF vectorizer for spam detection
   - Risk vector analysis: urgency, financial threats, phishing links
   - Stack: Python, Jupyter Notebook, Streamlit, FastAPI

4. **ai-resume-analyzer1** — JavaScript AI tool for resume analysis

5. **Personal-Portfolio** — TypeScript portfolio website (live on Vercel)

6. **ideaspark-studio** — TypeScript project

7. **localo** — TypeScript project

## WHY VAIBHAV FOR SCALER AI ENGINEER
- Builds production AI systems, not just tutorials (IncidentCommander is live on Hugging Face)
- Experience with AI agent evaluation frameworks — directly relevant to Scaler's AI products
- Strong Python + AI stack: FastAPI, LLM APIs, RAG, evaluation pipelines
- Competitive programmer with strong CS fundamentals (LeetCode 1713, CodeChef 1870)
- Full-stack capable: can own features end-to-end
- Hackathon track record: builds under pressure, ships working products

## CONVERSATION RULES
1. Keep answers SHORT — this is a phone call, not a presentation
2. Be natural and conversational: "Sure!", "Great question", "Absolutely"
3. If you don't know something specific, say: "I don't have that exact detail — you can ask Vaibhav directly during the interview"
4. NEVER make up facts
5. Handle interruptions naturally — just stop, say "Go ahead" and listen
6. For unknown projects not mentioned above, say: "That's not one I have details on right now"

## CALENDAR BOOKING FLOW
When someone wants to schedule:
1. Say: "Sure! What dates work best for you?"
2. Call check_availability with their date range
3. Offer 2-3 slots naturally: "I have Tuesday the 10th at 2 PM or Wednesday at 10 AM — which works?"
4. After they pick: "Perfect! Can I get your full name and email for the calendar invite?"
5. Call book_slot
6. Confirm: "Done! You're booked for [time]. You'll get a calendar invite at [email]. Looking forward to it!"

## OPENING
When the call starts, say naturally:
"Hi! I'm Sam, Vaibhav Pandey's AI representative. I can tell you about his background and projects, or we can set up an interview time. What would you like to know?"
"""

def delete_existing_assistants():
    """Delete any existing assistants to start fresh"""
    response = requests.get(f"https://api.vapi.ai/assistant", headers=headers)
    if response.status_code == 200:
        assistants = response.json()
        for assistant in assistants:
            requests.delete(f"https://api.vapi.ai/assistant/{assistant['id']}", headers=headers)
            print(f"Deleted assistant: {assistant['id']}")

def create_assistant():
    config = {
        "name": "Sam - Vaibhav's AI Persona",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "maxTokens": 200,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT}
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "check_availability",
                        "description": "Check Vaibhav's real calendar availability for interview slots",
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
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "book_slot",
                        "description": "Book a confirmed interview slot on Vaibhav's calendar",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "datetime": {
                                    "type": "string",
                                    "description": "Meeting datetime in ISO 8601 format"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Interviewer full name"
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Interviewer email for calendar invite"
                                }
                            },
                            "required": ["datetime", "name", "email"]
                        }
                    }
                }
            ]
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "pNInz6obpgDQGcFmaJgB",
            "stability": 0.4,
            "similarityBoost": 0.85,
            "optimizeStreamingLatency": 4,
            "useSpeakerBoost": True
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
        },
        "firstMessage": "Hi! I'm Sam, Vaibhav Pandey's AI representative. I can answer questions about his background and projects, or help schedule an interview. What would you like to know?",
        "serverUrl": f"{BACKEND_URL}/voice/webhook",
        "endCallFunctionEnabled": True,
        "recordingEnabled": True,
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "backgroundSound": "off",
        "backchannelingEnabled": False,
        "endCallPhrases": ["goodbye", "bye", "thank you bye", "that's all"]
    }

    response = requests.post("https://api.vapi.ai/assistant", headers=headers, json=config)
    
    if response.status_code == 201:
        assistant = response.json()
        print(f"Assistant created: {assistant['id']}")
        return assistant
    else:
        print(f"Error creating assistant: {response.status_code} - {response.text}")
        return None

def create_phone_number(assistant_id):
    # Try with area code
    config = {
        "provider": "vapi",
        "assistantId": assistant_id,
        "name": "Sam - Vaibhav AI Persona",
        "numberDesiredAreaCode": "986"
    }
    
    response = requests.post("https://api.vapi.ai/phone-number", headers=headers, json=config)
    
    if response.status_code == 201:
        phone = response.json()
        print(f"Phone number created: {phone.get('number', 'pending')}")
        return phone
    else:
        print(f"Error: {response.status_code} - {response.text}")
        # List existing numbers and link to new assistant
        list_response = requests.get("https://api.vapi.ai/phone-number", headers=headers)
        if list_response.status_code == 200:
            phones = list_response.json()
            if phones:
                phone_id = phones[0]['id']
                update = requests.patch(
                    f"https://api.vapi.ai/phone-number/{phone_id}",
                    headers=headers,
                    json={"assistantId": assistant_id}
                )
                if update.status_code == 200:
                    print(f"Linked existing phone: {phones[0].get('number')}")
                    return phones[0]
                else:
                    print(f"Link error: {update.text}")
            else:
                print("No existing phone numbers found")
        return None

def main():
    print("=" * 50)
    print("Setting up Vapi Voice Agent for Sam")
    print("=" * 50)
    
    # Clean up old assistants
    print("\nCleaning up old assistants...")
    delete_existing_assistants()
    
    # Create new assistant
    print("\nCreating assistant...")
    assistant = create_assistant()
    if not assistant:
        return
    
    # Create/link phone number
    print("\nSetting up phone number...")
    phone = create_phone_number(assistant['id'])
    
    print("\n" + "=" * 50)
    print("SETUP COMPLETE!")
    print("=" * 50)
    print(f"Assistant ID: {assistant['id']}")
    if phone:
        print(f"PHONE NUMBER: {phone.get('number', 'Check Vapi dashboard')}")
    print(f"Webhook URL: {BACKEND_URL}/voice/webhook")
    print("\nCall the phone number to talk to Sam!")

if __name__ == "__main__":
    main()
