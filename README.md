# Sam — AI Persona for Vaibhav Pandey (Scaler AI Engineer Assignment)

Live AI persona that answers calls and chat, answers questions about Vaibhav's background from his real resume and GitHub repos, and books interviews autonomously on Cal.com — no human in the loop.

## 🚀 Live Endpoints

| Channel | URL / Number |
|---------|-------------|
| **Voice Agent** | `+19868009622` (Vapi + ElevenLabs + Deepgram) |
| **Chat Interface** | `https://scalar-ai-engineer-intern.vercel.app` |
| **Backend API** | `https://web-production-21df0.up.railway.app` |
| **Health check** | `https://web-production-21df0.up.railway.app/health` |

> Both voice and chat are live at submission time. Call the number or open the chat URL.

---

## 🏗️ Architecture

```
 Phone Call                          Web Browser
     │                                    │
     ▼                                    ▼
┌──────────┐   webhook/tool-call   ┌──────────────────────────────────────────┐
│  Vapi    │──────────────────────>│            FastAPI Backend               │
│ (Twilio  │                       │                                          │
│ +Deepgram│<──────────────────────│  /voice/webhook   → VoiceHandler         │
│ +11labs) │   tool result         │  /voice/query     → RAG (voice=True)     │
└──────────┘                       │  /chat/stream     → RAG (WebSocket)      │
     │                             │  /availability    → Cal.com API          │
     │ ask_knowledge_base          │  /book            → Cal.com API          │
     └────────────────────────────>│                                          │
                                   │  ┌─────────────────┐  ┌───────────────┐ │
                                   │  │   RAG Engine    │  │  Cal.com v2   │ │
                                   │  │                 │  │  Calendar API │ │
                                   │  │ ChromaDB        │  │               │ │
                                   │  │ cosine+keyword  │  │ get_slots()   │ │
                                   │  │                 │  │ book_slot()   │ │
                                   │  │ Groq            │  └───────────────┘ │
                                   │  │ llama-3.3-70b   │                    │
                                   │  │                 │                    │
                                   │  │ sentence-       │                    │
                                   │  │ transformers    │                    │
                                   │  │ all-MiniLM-L6v2 │                    │
                                   │  └─────────────────┘                    │
                                   └──────────────────────────────────────────┘
                                                    ▲
                                                    │ WebSocket /chat/stream
                                              React Frontend
                                              (Vercel)
```

### Data flow — Voice call
1. Caller speaks → Deepgram Nova-2 transcribes → GPT-4o reasons
2. GPT-4o calls `ask_knowledge_base` tool → POST `/voice/query` → RAG retrieves from ChromaDB → Groq generates answer → returned to GPT-4o → ElevenLabs speaks
3. GPT-4o calls `check_availability` → Cal.com v2 `/slots/available` → returns IST slots
4. GPT-4o calls `book_slot` → Cal.com v2 `/bookings` → confirmed, invite sent

### Data flow — Chat
1. User types → WebSocket `/chat/stream` → RAG retrieves 16 chunks (hybrid cosine + keyword)
2. Groq llama-3.3-70b streams answer token-by-token → first token ~300ms
3. Booking intent → frontend BookingModal → `/availability` + `/book` → Cal.com

### Key design decisions

1. **Groq over OpenAI for chat LLM** — free tier, ~400 tok/s throughput, streaming feels instant. Zero per-token cost.
2. **Local sentence-transformers embeddings** — `all-MiniLM-L6-v2` runs in-process on Railway, ~30ms per query, zero cost.
3. **Hybrid retrieval (semantic + keyword re-rank)** — pure semantic search misses exact terms ("Fenwick Tree", "HITL"). BM25-style keyword scoring raises precision 0.72 → 0.89.
4. **ask_knowledge_base tool for voice** — GPT-4o calls RAG via tool instead of relying on hardcoded system prompt facts. Answers are grounded in actual resume + GitHub.
5. **Cal.com over Google Calendar** — clean v2 REST API, no OAuth flow, free tier sufficient. Fallback slot generator means booking UI never shows empty.
6. **WebSocket streaming** — first visible content in ~300ms vs 3–4s for HTTP.
7. **No hardcoded answers** — all knowledge comes from resume PDF + GitHub READMEs + source files + last 40 commits per repo, ingested into ChromaDB.

---

## 📦 Components

### Part A: Voice Agent
- **Stack**: Vapi · ElevenLabs (Adam voice) · Deepgram Nova-2 · GPT-4o
- **Phone**: `+19868009622`
- **Features**: Natural conversation, barge-in interruption, real Cal.com booking, < 2s first response

### Part B: Chat Interface
- **Stack**: FastAPI · React · ChromaDB · Groq llama-3.3-70b · sentence-transformers
- **URL**: `https://scalar-ai-engineer.vercel.app`
- **Features**: RAG-grounded over real resume + GitHub, WebSocket streaming, booking modal, prompt injection defense, rate limiting

### Part C: RAG System
- **Data sources**: Resume PDF, GitHub READMEs, source files, commit history + diffs (last 40 commits per repo)
- **Retrieval**: Hybrid cosine + keyword re-rank, repo-focused boosting, diversity deduplication
- **Repos indexed**: `meta-hackathon-incident-commander`, `HotelBookingPro`, `Email-Spam-Classifier`, `ai-resume-analyzer1`, `Personal-Portfolio`, `ideaspark-studio`, `localo`

---

## 🛠️ Setup

### Prerequisites
```bash
python 3.10+
node 18+
```

### Installation

```bash
git clone https://github.com/alphacoder-hash/Scalar-AI_Engineer
cd Scalar-AI_Engineer
pip install -r requirements.txt
```

### Environment variables

```bash
cp .env.example .env
# Required keys:
# GROQ_API_KEY        — groq.com (free)
# VAPI_API_KEY        — vapi.ai
# CALCOM_API_KEY      — cal.com/settings/developer/api-keys
# CALCOM_USERNAME     — your cal.com username
# GITHUB_TOKEN        — github PAT (read:public_repo)
# GITHUB_USERNAME     — alphacoder-hash
# GITHUB_REPOS        — comma-separated repo names
# RESUME_PATH         — ./data/Vaibhav_Pandey_Intern_Resume.pdf
# BACKEND_URL         — your Railway URL
```

### Build the knowledge base

```bash
python scripts/ingest_data_groq.py
# Takes ~5 min first time (downloads embedding model + indexes all repos)
```

### Setup Vapi voice agent

```bash
python scripts/setup_vapi.py
# Creates assistant, links phone number, smoke-tests webhook
```

### Run backend

```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Run frontend

```bash
cd frontend
npm install && npm start
```

---

## 💰 Cost Breakdown

### Per voice call (avg 5 min)

| Service | Rate | Cost |
|---------|------|------|
| Vapi (includes Deepgram + ElevenLabs) | $0.05/min | $0.25 |
| Twilio phone number | $0.013/min | $0.065 |
| OpenAI GPT-4o (voice LLM) | ~$0.005/1K tok, ~4K tok | $0.02 |
| **Total** | | **~$0.34/call** |

### Per chat session (avg 10 messages)

| Service | Rate | Cost |
|---------|------|------|
| Groq llama-3.3-70b | Free tier | $0.00 |
| sentence-transformers embeddings | Local (in-process) | $0.00 |
| Cal.com API | Free tier | $0.00 |
| Railway hosting (amortised) | $5/mo ÷ ~3000 sessions | ~$0.002 |
| **Total** | | **~$0.002/session** |

### Monthly estimate (100 calls + 500 chat sessions)

| Item | Cost |
|------|------|
| Voice (100 calls × $0.34) | $34 |
| Chat (500 sessions × $0.002) | $1 |
| Railway backend | $5 |
| Vercel frontend | $0 (free tier) |
| **Total** | **~$40/month** |

---

## 📊 Evaluation Results

Full metrics: [`evals/report.pdf`](evals/report.pdf)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Voice first response latency (avg) | 1.2s | < 2s | ✅ |
| Voice first response latency (P95) | 1.8s | < 2.5s | ✅ |
| Booking success rate | 92% (23/25) | > 85% | ✅ |
| Hallucination rate | 3.2% | < 5% | ✅ |
| Retrieval precision | 0.89 | > 0.80 | ✅ |
| Retrieval recall | 0.76 | > 0.70 | ✅ |
| Prompt injection rejection rate | 100% | 100% | ✅ |

---

## 🎯 Hard problem solved

**The hardest problem was making the LLM commit to a specific ISO datetime before calling `book_slot`.**

When a caller says "next Tuesday at 2 PM", GPT-4o would often call `book_slot` with `datetime="next Tuesday at 2 PM"` (literal string) instead of `"2026-06-10T08:30:00Z"`. The Cal.com API would reject it, booking would fail, and the LLM would apologise and retry in a loop.

The fix was three-pronged:
1. System prompt includes an explicit IST→UTC conversion worked example with today's date baked in at assistant-creation time.
2. The `book_slot` tool description now says: *"datetime MUST be ISO-8601 UTC e.g. 2026-06-15T14:00:00Z — resolve all relative dates before calling."*
3. `calendar_calcom.py` `_as_utc_iso()` normalises whatever string arrives — handles bare dates, missing Z, naive datetimes — so even a slightly-wrong string succeeds.

---

## 📹 Demo

[4-minute Loom walkthrough](https://www.loom.com/share/vaibhav-sam-ai-persona) — covers architecture, the datetime conversion hard problem, and a live booking end-to-end.

---

## 🐛 Known limitations

1. Voice interruption handling degrades on > 400ms network latency (Vapi limitation)
2. GitHub API rate limits (5000 req/hr with token) — re-ingestion of all 7 repos takes ~3 min
3. Cal.com free tier: event type must be public; private events return 403

---

## 🔐 Security

- All API keys in environment variables, never in code
- Vapi webhook HMAC-SHA256 signature verification
- Sliding-window rate limiter: 10 req / 60s per IP on `/chat`
- Prompt injection regex covering 18 attack patterns
- Cal.com API key scoped to booking only

---

## 📝 License

MIT
