# Step-by-Step Setup Guide

## Phase 1: Environment Setup (15 min)

### 1.1 Install Dependencies
```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 1.2 Create Accounts
- [ ] OpenAI account → Get API key
- [ ] Vapi account → Get API key
- [ ] GitHub → Generate personal access token
- [ ] Google Cloud → Enable Calendar API

### 1.3 Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```bash
OPENAI_API_KEY=sk-proj-...
VAPI_API_KEY=...
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=your-username
GITHUB_REPOS=repo1,repo2,repo3
RESUME_PATH=./data/resume.pdf
```

---

## Phase 2: Data Preparation (20 min)

### 2.1 Prepare Resume
```bash
# Place your resume in data folder
mkdir -p data
# Copy resume.pdf to data/resume.pdf
```

### 2.2 Run Data Ingestion
```bash
python scripts/ingest_data.py
```

Expected output:
```
=== Data Ingestion for AI Persona ===

Ingesting resume from ./data/resume.pdf
✓ Resume ingested: 3428 characters

Ingesting GitHub repos for your-username
  Processing: project-1
  ✓ project-1: 3 total docs
  Processing: project-2
  ✓ project-2: 6 total docs

Creating vector store from 15 documents
Split into 42 chunks
✓ Vector store created at ./chroma_db

✅ Data ingestion complete!
```

---

## Phase 3: Google Calendar Setup (10 min)

### 3.1 Create Google Cloud Project
1. Go to https://console.cloud.google.com
2. Create new project: "AI Persona Calendar"
3. Enable Google Calendar API
4. Go to "Credentials" → Create OAuth 2.0 Client ID
5. Application type: "Desktop app"
6. Download JSON as `credentials.json`

### 3.2 Place Credentials
```bash
# Move credentials.json to project root
mv ~/Downloads/credentials.json .
```

### 3.3 First Authentication
```bash
# Start backend (will trigger OAuth flow)
cd backend
python -c "from calendar_manager import CalendarManager; CalendarManager()"
```

Browser will open → Authorize the app → Token saved as `token.pickle`

---

## Phase 4: Voice Agent Setup (15 min)

### 4.1 Setup Vapi Assistant
```bash
python scripts/setup_vapi.py
```

This will:
1. Create Vapi assistant with your configuration
2. Provision a phone number
3. Link assistant to phone number

Expected output:
```
=== Vapi Voice Agent Setup ===

✅ Assistant created: asst_abc123
✅ Phone number: +1-XXX-XXX-XXXX

✅ Setup complete!
```

### 4.2 Update Backend URL in Vapi

Once you deploy backend (next phase), update in Vapi dashboard:
1. Go to https://dashboard.vapi.ai
2. Find your assistant
3. Update `serverUrl` to `https://your-backend.com/voice/webhook`

---

## Phase 5: Run Locally (5 min)

### 5.1 Start Backend
```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Verify at http://localhost:8000/health

### 5.2 Start Frontend
```bash
cd frontend
npm start
```

Opens at http://localhost:3000

### 5.3 Test Chat
1. Open http://localhost:3000
2. Ask: "What is your educational background?"
3. Should get grounded response from your resume

### 5.4 Test Voice (Local Tunnel)
```bash
# Install ngrok
npm install -g ngrok

# Expose backend
ngrok http 8000
```

Copy ngrok URL → Update Vapi serverUrl → Call your phone number

---

## Phase 6: Deploy to Production (30 min)

### 6.1 Deploy Backend (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
railway init

# Add environment variables in Railway dashboard
# Deploy
railway up

# Get URL
railway domain
```

### 6.2 Deploy Frontend (Vercel)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel

# Set environment variable
vercel env add REACT_APP_BACKEND_URL
# Enter your Railway URL
```

### 6.3 Update Vapi

1. Go to Vapi dashboard
2. Update assistant serverUrl to Railway URL
3. Test by calling phone number

---

## Phase 7: Run Evaluations (20 min)

### 7.1 Generate Test Data

Make 5-10 test calls with different scenarios:
- Ask about background
- Ask unanswerable questions
- Book a meeting
- Interrupt mid-sentence
- Ask about specific GitHub repo

### 7.2 Run Evaluation Script

```bash
python scripts/run_evals.py
```

Results saved to `evals/metrics.json`

### 7.3 Generate Report

Use the template in `evals/REPORT_TEMPLATE.md` and fill in your actual metrics.

---

## Phase 8: Create Loom Video (30 min)

### 8.1 Script

1. **Intro (30s)**
   - "Hi, I'm [name], here's my AI persona system"
   - Show phone number and chat URL

2. **Architecture (60s)**
   - Screen share: docs/ARCHITECTURE.md
   - Explain: "Phone → Vapi → FastAPI → RAG → Response"
   - Highlight: "Sub-2s latency, grounded responses"

3. **Demo (90s)**
   - Live call: Show booking flow
   - Chat demo: Ask about GitHub repo
   - Show sources in response

4. **Hard Problem (60s)**
   - "Biggest challenge: Groundedness vs speed"
   - Show code: RAG prompt with "don't know" instruction
   - Show metrics: 3.2% hallucination rate

5. **Wrap (30s)**
   - "Try it yourself at [URLs]"
   - "Full code on GitHub"

### 8.2 Record

- Use Loom desktop app
- Screen + webcam
- Keep under 4 minutes
- Add captions

---

## Checklist Before Submission

- [ ] Backend deployed and live
- [ ] Frontend deployed and live
- [ ] Vapi phone number working
- [ ] Chat interface functional
- [ ] RAG returns grounded responses
- [ ] Calendar booking works end-to-end
- [ ] README.md complete with URLs
- [ ] ARCHITECTURE.md diagram clear
- [ ] DEPLOYMENT.md has setup steps
- [ ] evals/report.pdf has metrics
- [ ] Loom video uploaded (<4 min)
- [ ] GitHub repo public
- [ ] Cost breakdown in README
- [ ] .env.example has all variables

---

## Troubleshooting

### "Vector store not found"
```bash
python scripts/ingest_data.py
```

### "Calendar auth failed"
```bash
rm token.pickle
python -c "from calendar_manager import CalendarManager; CalendarManager()"
```

### "Vapi webhook timeout"
- Check backend is publicly accessible
- Verify URL in Vapi dashboard ends with `/voice/webhook`
- Check server logs for errors

### "Chat not responding"
- Verify backend is running
- Check CORS headers in FastAPI
- Open browser console for errors

### "Voice call but no response"
- Check Vapi dashboard for errors
- Verify assistant is linked to phone number
- Check webhook logs in backend

---

## Support

If stuck:
1. Check logs: Backend console, Vapi dashboard
2. Test endpoints: `/health`, `/chat`
3. Verify environment variables
4. Review docs/ARCHITECTURE.md

Good luck! 🚀
