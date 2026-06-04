# Quick Start Guide

## 🚀 Get Running in 10 Minutes

### Step 1: Install Dependencies (2 min)
```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Step 2: Configure (3 min)
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add:
# - OPENAI_API_KEY (required)
# - VAPI_API_KEY (for voice)
# - GITHUB_USERNAME (your GitHub username)
# - GITHUB_REPOS (comma-separated repo names)
```

### Step 3: Prepare Data (3 min)
```bash
# Place your resume in data/
mkdir -p data
# Copy your resume.pdf to data/resume.pdf

# Run data ingestion
python scripts/ingest_data.py
```

### Step 4: Run Locally (2 min)
```bash
# Terminal 1: Backend
cd backend
python -m uvicorn app:app --reload

# Terminal 2: Frontend
cd frontend
npm start
```

### Step 5: Test
- Chat: http://localhost:3000
- Backend health: http://localhost:8000/health

---

## 📱 Setup Voice Agent

### Get Vapi Phone Number
```bash
# Set VAPI_API_KEY in .env first
python scripts/setup_vapi.py
```

### Expose Backend for Webhooks
```bash
# Install ngrok
npm install -g ngrok

# Expose backend
ngrok http 8000

# Copy the ngrok URL and update in Vapi dashboard
```

---

## 🧪 Run Evaluations
```bash
python scripts/eval_system.py
```

Results saved to `evals/metrics.json`

---

## 🚢 Deploy

### Backend (Railway)
```bash
railway login
railway init
railway up
```

### Frontend (Vercel)
```bash
cd frontend
vercel
```

### Update Vapi
Go to https://dashboard.vapi.ai and update serverUrl to your Railway URL

---

## ✅ Checklist

- [ ] `pip install -r requirements.txt` works
- [ ] `.env` file configured
- [ ] `data/resume.pdf` exists
- [ ] `python scripts/ingest_data.py` completes
- [ ] Backend runs at http://localhost:8000
- [ ] Frontend runs at http://localhost:3000
- [ ] Chat responds with grounded answers
- [ ] Vapi phone number provisioned
- [ ] Calendar auth completed (if using)
- [ ] Evaluations run successfully

---

## 🆘 Troubleshooting

**"Vector store not found"**
```bash
python scripts/ingest_data.py
```

**"Module not found"**
```bash
pip install -r requirements.txt
```

**Chat not responding**
- Check backend is running
- Check OPENAI_API_KEY in .env
- Look at backend console for errors

**Voice not working**
- Verify VAPI_API_KEY
- Check serverUrl in Vapi dashboard
- Ensure ngrok/deployed backend is accessible

---

## 📚 Next Steps

1. Read [SETUP.md](SETUP.md) for detailed instructions
2. Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design
3. Check [evals/REPORT_TEMPLATE.md](evals/REPORT_TEMPLATE.md) for evaluation format
4. See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment

---

## 🎯 What You're Building

**Part A: Voice Agent**
- Call phone number → AI answers questions → Books interview
- Target: <2s latency, handles interruptions

**Part B: Chat Interface**
- Web chat → RAG-grounded responses → Calendar booking
- Defends against prompt injection, admits when doesn't know

**Part C: Evaluation**
- Measure voice latency, booking success rate
- Measure chat hallucination rate, retrieval quality
- Document 3 failure modes and fixes

Good luck! 🚀
