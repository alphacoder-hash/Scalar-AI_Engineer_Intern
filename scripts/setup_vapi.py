"""
Run once to create/update the Vapi assistant and link a phone number.
  python scripts/setup_vapi.py
"""
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "https://scalar-aiengineerintern-production.up.railway.app")

HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are Sam — Vaibhav Pandey's AI representative on a live phone call.

## VOICE RULES (critical)
- Max 2 sentences per turn. This is a phone call, not a presentation.
- Be warm and natural: "Sure!", "Absolutely", "Great question", "Got it".
- If interrupted mid-sentence, stop immediately, say "Go ahead" and listen.
- If you don't know something: "I don't have that detail — Vaibhav can cover it in the actual interview."
- NEVER invent facts. If uncertain, say so.
- Do not read bullet lists aloud — weave info into natural sentences.

## VAIBHAV'S PROFILE

**Personal:** CS undergrad (Class of 2027), Vadodara, India.
Email: Vpandey1707@gmail.com | GitHub: github.com/alphacoder-hash

**Recent Experience:**
- Centific Premier Hackathon 2.0 (Apr–May 2026, Hyderabad): Built an AI Business Analyst Agent in an Agentic SDLC platform. Ingested PDFs, DOCX, emails, and meeting notes to auto-generate Features, Epics, and User Stories. Added Human-in-the-Loop (HITL) validation with confidence scoring.

**Key Projects:**
1. IncidentCommander (Meta Hackathon) — Production OpenEnv for evaluating AI agents as SREs. Simulates 8-service microservices with cascading failures across 4 difficulty levels. Live: vaibhav0714-incidentcommander.hf.space. Stack: Python, FastAPI, Docker, Gradio, OpenAI.
2. HotelBookingPro — TypeScript full-stack booking system with JWT auth and dynamic pricing via Segment Trees.
3. Email-Spam-Classifier — scikit-learn TF-IDF model with risk vector analysis (urgency, phishing, financial threats). Stack: Python, Streamlit, FastAPI.

**Skills:** Python, TypeScript, JavaScript, Java, C++. FastAPI, React, Node. LLM apps, RAG, prompt engineering, AI evaluation, HITL pipelines, scikit-learn, vector DBs (ChromaDB), REST APIs.

**Competitive Programming:** LeetCode max 1713 · CodeChef 4-star max 1870.
**Hackathons:** SIH 2025 institute qualifier · Grand Finalist PU Code 2.0 & 3.0 · Vadodara Hackathon 6.0.

## WHY VAIBHAV FOR SCALER AI ENGINEER
He ships real AI systems under pressure (IncidentCommander is live on HuggingFace). He has direct experience building AI evaluation frameworks — exactly what Scaler needs. Strong Python + LLM stack, full-stack capable, competitive programmer with solid CS fundamentals.

## BOOKING FLOW
1. "Sure! What dates work for you?"
2. Call check_availability with their range.
3. Offer 2-3 slots naturally: "I have Tuesday the 10th at 2 PM or Wednesday at 10 AM — which works?"
4. "Perfect! Can I get your full name and email for the invite?"
5. Call book_slot.
6. "Done! You're booked for [time]. Invite goes to [email]. Looking forward to it!"

## OPENING LINE
"Hi! I'm Sam, Vaibhav Pandey's AI representative. I can tell you about his background and projects, or we can set up an interview time. What would you like to know?"
"""

# ── Tools ─────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check Vaibhav's real calendar for open interview slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date":   {"type": "string", "description": "End date YYYY-MM-DD"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_slot",
            "description": "Book a confirmed 30-minute interview on Vaibhav's calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "datetime": {"type": "string", "description": "ISO-8601 datetime e.g. 2025-07-15T14:00:00Z"},
                    "name":     {"type": "string", "description": "Interviewer full name"},
                    "email":    {"type": "string", "description": "Interviewer email for calendar invite"},
                },
                "required": ["datetime", "name", "email"],
            },
        },
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _req(method, path, **kwargs):
    url = f"https://api.vapi.ai{path}"
    r = getattr(requests, method)(url, headers=HEADERS, **kwargs)
    return r

def delete_all_assistants():
    r = _req("get", "/assistant")
    if r.status_code == 200:
        for a in r.json():
            _req("delete", f"/assistant/{a['id']}")
            print(f"  Deleted assistant {a['id']}")

def create_assistant():
    config = {
        "name": "Sam — Vaibhav's AI Persona",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.4,
            "maxTokens": 180,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "tools": TOOLS,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "pNInz6obpgDQGcFmaJgB",  # Adam — clear, natural
            "stability": 0.45,
            "similarityBoost": 0.85,
            "optimizeStreamingLatency": 4,
            "useSpeakerBoost": True,
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en",
        },
        "firstMessage": (
            "Hi! I'm Sam, Vaibhav Pandey's AI representative. "
            "I can answer questions about his background, or help schedule an interview. "
            "What would you like to know?"
        ),
        "serverUrl": f"{BACKEND_URL}/voice/webhook",
        "serverUrlSecret": os.getenv("VAPI_SERVER_SECRET", ""),
        "recordingEnabled": True,
        "endCallFunctionEnabled": True,
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "backgroundSound": "off",
        "backchannelingEnabled": False,
        "endCallPhrases": ["goodbye", "bye", "thanks bye", "that's all"],
        # Let the model handle interruptions naturally via short maxTokens
        "responseDelaySeconds": 0,
        "llmRequestDelaySeconds": 0,
    }
    r = _req("post", "/assistant", json=config)
    if r.status_code == 201:
        a = r.json()
        print(f"  Assistant created: {a['id']}")
        return a
    print(f"  ERROR creating assistant: {r.status_code} {r.text[:400]}")
    return None

def setup_phone(assistant_id: str):
    """Buy a new Vapi number or re-link an existing one to the new assistant."""
    # Try to buy
    r = _req("post", "/phone-number", json={
        "provider": "vapi",
        "assistantId": assistant_id,
        "name": "Sam — Vaibhav AI Persona",
        "numberDesiredAreaCode": "415",
    })
    if r.status_code == 201:
        phone = r.json()
        print(f"  Phone number provisioned: {phone.get('number')}")
        return phone

    # Fall back: re-link first existing number
    lr = _req("get", "/phone-number")
    if lr.status_code == 200:
        phones = lr.json()
        if phones:
            pid = phones[0]["id"]
            ur = _req("patch", f"/phone-number/{pid}", json={"assistantId": assistant_id})
            if ur.status_code == 200:
                print(f"  Linked existing phone: {phones[0].get('number')}")
                return phones[0]
    print(f"  Could not provision/link phone: {r.status_code} {r.text[:300]}")
    return None

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not VAPI_API_KEY:
        print("ERROR: VAPI_API_KEY not set in .env")
        return

    print("\n=== Vapi Setup ===")
    print("Removing old assistants...")
    delete_all_assistants()

    print("Creating assistant...")
    assistant = create_assistant()
    if not assistant:
        return

    print("Setting up phone number...")
    phone = setup_phone(assistant["id"])

    print("\n=== DONE ===")
    print(f"Assistant ID : {assistant['id']}")
    if phone:
        print(f"PHONE NUMBER : {phone.get('number', 'check Vapi dashboard')}")
    print(f"Webhook URL  : {BACKEND_URL}/voice/webhook")
    print("\nUpdate REACT_APP_PHONE_NUMBER in frontend/.env then redeploy frontend.")

if __name__ == "__main__":
    main()
