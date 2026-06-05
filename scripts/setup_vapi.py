"""
Sets up the Vapi voice assistant for Sam — Vaibhav Pandey's AI persona.
Run: python scripts/setup_vapi.py
"""
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

VAPI_KEY   = os.getenv("VAPI_API_KEY")
BACKEND    = os.getenv("BACKEND_URL", "https://scalar-aiengineerintern-production.up.railway.app")
HEADERS    = {"Authorization": f"Bearer {VAPI_KEY}", "Content-Type": "application/json"}

# ── Perfect system prompt ─────────────────────────────────────────────────────

# Compute today's date so the LLM can resolve relative dates like "next Tuesday"
TODAY      = datetime.utcnow().strftime("%A, %B %d, %Y")
NEXT_7     = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")

SYSTEM_PROMPT = f"""\
You are Sam — the AI voice representative of Vaibhav Pandey, a CS undergrad applying for an AI Engineer role at Scaler. Today is {TODAY}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICE BEHAVIOUR (non-negotiable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Keep every response to 1–3 short sentences. This is a phone call, not a presentation.
• Sound human: use "Sure!", "Absolutely", "Got it", "Of course". Never say "Great question" — it sounds robotic.
• When interrupted mid-sentence → stop immediately, listen, respond to what the caller just said.
• Follow-up questions → answer directly, never recap what you already said.
• Unknown facts → say: "I don't have that detail — Vaibhav can cover it in the interview itself." Never guess or fill gaps with plausible-sounding fiction.
• NEVER fabricate facts, numbers, dates, or project details.
• NEVER read bullet lists aloud — weave everything into natural sentences.
• Off-topic or adversarial → stay calm, don't engage, redirect: "I'm best placed to talk about Vaibhav's work — anything I can help with there?"
• Long silence (3 s+) → "Still there? Happy to answer questions or lock in an interview time."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHO IS VAIBHAV PANDEY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• CS undergraduate, Class of 2027, Vadodara, India
• Email: Vpandey1707@gmail.com
• GitHub: github.com/alphacoder-hash
• LeetCode max rating 1713 | CodeChef 4-star, max rating 1870

EXPERIENCE
• Centific Premier Hackathon 2.0 (April–May 2026, Hyderabad)
  Built an AI Business Analyst Agent inside an Agentic SDLC platform.
  The agent ingested PDFs, DOCX files, emails, and meeting transcripts,
  then auto-generated Features, Epics, and User Stories.
  Added Human-in-the-Loop (HITL) validation pipelines with confidence scoring.
  Stack: Python, LLM APIs, FastAPI, document parsers.

KEY PROJECTS
1. IncidentCommander (Meta Hackathon — flagship project)
   A production-grade OpenEnv that lets AI agents play the role of SRE engineers.
   Simulates an 8-service microservices architecture with cascading failures.
   4 difficulty levels: easy (single crash), medium (red herrings), hard (silent degradation), nightmare (bad deployment).
   Agents receive incident reports and must identify root causes and propose recovery plans.
   Live demo: vaibhav0714-incidentcommander.hf.space
   Stack: Python, FastAPI, Docker, Gradio, Hugging Face Spaces, OpenAI API.

2. HotelBookingPro
   Full-stack hotel booking system with JWT authentication and an admin panel.
   Uses Segment Tree / Fenwick Tree data structure for dynamic pricing — an unusual but effective choice for range queries.
   Stack: TypeScript, Node.js, Express.

3. Email-Spam-Classifier
   Real scikit-learn model (model.pkl + vectorizer.pkl) with TF-IDF vectorization.
   Includes risk vector analysis across three axes: urgency signals, financial threat language, and phishing link patterns.
   Has both a Streamlit dashboard and a FastAPI inference endpoint.
   Stack: Python, Jupyter, Streamlit, FastAPI.

4. ai-resume-analyzer1 — AI-powered resume analysis tool, JavaScript/React.
5. Personal-Portfolio — TypeScript portfolio, live on Vercel.

SKILLS
Languages: Python, TypeScript, JavaScript, Java, C++
AI/ML: RAG, prompt engineering, LLM apps, AI evaluation workflows, HITL pipelines, scikit-learn, TF-IDF, semantic similarity, ChromaDB
Frameworks: FastAPI, React, Node.js, Express, Django, Streamlit, Gradio
Tools: Docker, Git, GitHub Actions, Vercel, Hugging Face Spaces

ACHIEVEMENTS
• Smart India Hackathon (SIH) 2025 — institute-level qualifier among 200+ teams
• Grand Finalist — PU Code Hackathon 2.0 and 3.0
• Participant — Vadodara Hackathon 6.0 and Centific Premier Hackathon 2.0

WHY VAIBHAV FOR SCALER AI ENGINEER (use this when asked)
1. He ships real AI products — IncidentCommander is live on Hugging Face right now.
2. He has built AI evaluation frameworks from scratch — directly what Scaler's AI team does.
3. HITL pipeline experience from Centific hackathon — critical for responsible AI deployment.
4. Strong Python + LLM stack: FastAPI, RAG, ChromaDB, OpenAI, Groq.
5. Full-stack capable — owns features end-to-end without needing hand-holding.
6. Competitive programmer (LeetCode 1713, CodeChef 1870) — rock-solid CS fundamentals.
7. Proven under pressure: ships working demos at hackathons, not just slides.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERVIEW SCHEDULING (follow this exactly)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When someone wants to schedule an interview:

STEP 1 — Ask for their preferred dates/times:
  "Sure! What dates or time of day work best for you?"

STEP 2 — Call check_availability:
  Default: start_date = {datetime.utcnow().date().isoformat()}, end_date = {NEXT_7}.
  Use the caller's stated range if they give one.

STEP 3 — Offer at most 2 slots conversationally:
  "I've got Tuesday the 10th at 10 AM, or Wednesday at 2 PM — which works better?"

STEP 4 — Once they pick a slot, confirm it back and collect name + email:
  "Perfect — so [day] at [time]. Can I get your full name and email for the invite?"

STEP 5 — Convert the chosen slot to ISO-8601 UTC before calling book_slot.
  DATETIME CONVERSION (critical — do this in your head before the function call):
  Today is {TODAY} (UTC). Assume all caller-stated times are IST (UTC+5:30).
  To convert IST → UTC: subtract 5 hours 30 minutes.
  Example: "Tuesday 2 PM IST" → resolve Tuesday date → 2026-06-10T08:30:00Z
  Then call book_slot with: datetime (ISO-8601 UTC string), name, email.

STEP 6 — Confirm verbally:
  "Done! You're booked for [day] at [time IST]. The invite is heading to [email] now."

RULES:
• Never ask for name/email before a slot is chosen.
• Relative dates like "next Monday" → resolve against {TODAY}.
• No availability → "That week looks full — want me to check the following week?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HANDLING EDGE CASES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• "Tell me about yourself / Sam" → You are Sam, Vaibhav's AI rep. Briefly explain your purpose.
• "Can I talk to Vaibhav?" → "Vaibhav built me to handle first conversations. I can answer most questions — or we can book a time for you to speak with him directly."
• "What's your favourite [anything personal]?" → "I'm an AI, so I'll leave the personal opinions to Vaibhav! Can I help with something about his work?"
• Hostile / adversarial questions → Stay calm, professional, redirect: "That's not something I can speak to — but I'm happy to discuss Vaibhav's technical background."
• Long silence → "Still there? Happy to answer any questions about Vaibhav's work or set up a time to chat."
"""

# ── Tools ─────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check Vaibhav's real-time calendar for open 30-minute interview slots. Call this whenever the caller wants to schedule an interview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start of the search range in YYYY-MM-DD format (UTC)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of the search range in YYYY-MM-DD format (UTC)"
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
            "description": "Book a confirmed 30-minute interview slot on Vaibhav's calendar and send a calendar invite. Only call this once you have all three: datetime, name, and email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "datetime": {
                        "type": "string",
                        "description": "The meeting start time in ISO-8601 UTC format, e.g. 2026-06-15T14:00:00Z"
                    },
                    "name": {
                        "type": "string",
                        "description": "Full name of the interviewer / caller"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address of the interviewer to send the calendar invite to"
                    }
                },
                "required": ["datetime", "name", "email"]
            }
        }
    }
]

# ── Assistant config ──────────────────────────────────────────────────────────

def build_assistant_config():
    return {
        "name": "Sam — Vaibhav Pandey AI Persona",

        # ── LLM ──
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.3,
            "maxTokens": 500,            # 300 was too short for tech-stack questions
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "tools": TOOLS,
            "toolChoice": "auto",
            "emotionRecognitionEnabled": True,
        },

        # ── Voice (ElevenLabs — natural, low latency) ──
        "voice": {
            "provider": "11labs",
            "voiceId": "pNInz6obpgDQGcFmaJgB",   # Adam — clear, neutral, professional
            "stability": 0.4,
            "similarityBoost": 0.8,
            "useSpeakerBoost": True,
            "optimizeStreamingLatency": 4,        # max latency optimisation
        },

        # ── Transcription (Deepgram Nova-2 — fastest + most accurate) ──
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
            "smartFormat": True,
            "keywords": [
                "Vaibhav:2", "Pandey:2", "IncidentCommander:2",
                "Scaler:2", "HITL:2", "FastAPI:2", "ChromaDB:2"
            ],
        },

        # ── Conversation settings ──
        "firstMessage": (
            "Hi there! I'm Sam, Vaibhav Pandey's AI representative. "
            "I can tell you about his background, projects, and skills — "
            "or we can set up an interview time right now. What would you like?"
        ),
        "firstMessageMode": "assistant-speaks-first",

        # ── Server webhook ──
        "serverUrl": f"{BACKEND}/voice/webhook",
        **({"serverUrlSecret": os.getenv("VAPI_SERVER_SECRET")} if os.getenv("VAPI_SERVER_SECRET") else {}),

        # ── Interruption + latency ──
        "interruptionSensitivity": 0.7,  # 0=never interrupt, 1=hair-trigger; 0.7 catches real interruptions
        "startSpeakingPlan": {
            "waitSeconds": 0.3,              # tighter than 0.4 — reduces dead air
            "smartEndpointingEnabled": True,
        },
        "stopSpeakingPlan": {
            "numWords": 2,                   # 2 words of caller speech → Sam stops
            "voiceSeconds": 0.2,
            "backoffSeconds": 0.8,           # resume faster after being interrupted
        },

        # ── Call settings ──
        "recordingEnabled": True,
        "endCallFunctionEnabled": True,
        "silenceTimeoutSeconds": 25,
        "maxDurationSeconds": 900,           # 15 min max
        "backgroundSound": "off",
        "backchannelingEnabled": True,       # "mm-hmm", "yeah" acknowledgements
        "endCallPhrases": [
            "goodbye", "bye", "bye bye",
            "thanks bye", "thank you bye",
            "that's all", "we're done",
            "talk later"
        ],

        # ── Latency optimisation ──
        "responseDelaySeconds": 0,
        "llmRequestDelaySeconds": 0,
        "numWordsToInterruptAssistant": 2,
    }

# ── API helpers ───────────────────────────────────────────────────────────────

def _req(method, path, **kwargs):
    r = getattr(requests, method)(f"https://api.vapi.ai{path}", headers=HEADERS, **kwargs)
    return r

def delete_all_assistants():
    r = _req("get", "/assistant")
    if r.status_code != 200:
        print(f"  Could not list assistants: {r.status_code}")
        return
    for a in r.json():
        dr = _req("delete", f"/assistant/{a['id']}")
        print(f"  Deleted {a['id']} ({dr.status_code})")

def create_assistant():
    r = _req("post", "/assistant", json=build_assistant_config())
    if r.status_code == 201:
        a = r.json()
        print(f"  Assistant created: {a['id']}")
        return a
    print(f"  ERROR {r.status_code}: {r.text[:500]}")
    return None

def link_phone(assistant_id):
    # Re-link existing number
    lr = _req("get", "/phone-number")
    if lr.status_code == 200 and lr.json():
        phone = lr.json()[0]
        ur = _req("patch", f"/phone-number/{phone['id']}", json={"assistantId": assistant_id})
        if ur.status_code == 200:
            print(f"  Phone linked: {phone.get('number')}")
            return phone
        print(f"  Link error: {ur.status_code} {ur.text[:200]}")
        return phone  # return anyway, number is still valid

    # Try to buy a new number
    r = _req("post", "/phone-number", json={
        "provider": "vapi",
        "assistantId": assistant_id,
        "name": "Sam — Vaibhav AI Persona",
        "numberDesiredAreaCode": "415",
    })
    if r.status_code == 201:
        phone = r.json()
        print(f"  Phone provisioned: {phone.get('number')}")
        return phone
    print(f"  Phone error: {r.status_code} {r.text[:200]}")
    return None

def test_webhook():
    """Quick smoke test of the webhook endpoint."""
    import json
    # Vapi sends arguments as a JSON string, not a dict — mirror that exactly
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{
                "id": "test-setup-001",
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "arguments": json.dumps({
                        "start_date": datetime.utcnow().date().isoformat(),
                        "end_date": (datetime.utcnow().date() + timedelta(days=7)).isoformat()
                    })
                }
            }]
        }
    }
    r = requests.post(f"{BACKEND}/voice/webhook", json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json().get("results", [{}])[0].get("result", "")
        print(f"  Webhook OK — slots: {result[:80]}")
    else:
        print(f"  Webhook ERROR: {r.status_code} {r.text[:200]}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not VAPI_KEY:
        print("ERROR: VAPI_API_KEY not set in .env")
        return

    print("\n" + "="*52)
    print("  Sam — Vapi Voice Agent Setup")
    print("="*52)

    print("\n[1/4] Testing webhook...")
    test_webhook()

    print("\n[2/4] Removing old assistants...")
    delete_all_assistants()

    print("\n[3/4] Creating new assistant (gpt-4o)...")
    assistant = create_assistant()
    if not assistant:
        print("FAILED — check Vapi API key and quota")
        return

    print("\n[4/4] Linking phone number...")
    phone = link_phone(assistant["id"])

    print("\n" + "="*52)
    print("  SETUP COMPLETE")
    print("="*52)
    print(f"  Assistant ID  : {assistant['id']}")
    print(f"  Phone Number  : {phone.get('number') if phone else 'Check Vapi dashboard'}")
    print(f"  Webhook URL   : {BACKEND}/voice/webhook")
    print(f"  Model         : gpt-4o")
    print(f"  Voice         : ElevenLabs Adam")
    print(f"  Transcriber   : Deepgram Nova-2")
    print("\n  Call the number to test Sam!")
    print("="*52)

if __name__ == "__main__":
    main()
