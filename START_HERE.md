# Sam - AI Persona Complete Setup

## ✅ SETUP COMPLETE!

Everything is configured for **Vaibhav Pandey**.

### What's Ready:
- ✅ Resume ingested (Vaibhav_Pandey_Intern_Resume.pdf)
- ✅ GitHub repos indexed (7 repos, 63 chunks)
- ✅ Free Groq LLM (Llama 3.1 70B)
- ✅ Free local embeddings (Sentence Transformers)
- ✅ Cal.com calendar integration
- ✅ Vapi voice agent configured

---

## 🚀 RUN THE SYSTEM

### Option 1: Quick Start (Windows)
```bash
# Open terminal in project folder and run:
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Test First
```bash
# Check everything works:
chcp 65001
python scripts\check_setup.py

# Then start backend:
cd backend
python -m uvicorn app:app --reload
```

---

## 📍 Access Points

Once backend is running:

- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Chat API**: POST to http://localhost:8000/chat

### Test the Chat API:
```bash
curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"What is Vaibhav's background?\"}"
```

---

## 🎤 Setup Voice Agent

1. **Start backend** (must be running)
2. **Expose publicly** (so Vapi can call webhooks):
   ```bash
   # Install ngrok
   npm install -g ngrok

   # Expose backend
   ngrok http 8000
   ```

3. **Update Vapi**:
   - Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)
   - Go to https://dashboard.vapi.ai
   - Find your assistant
   - Update `serverUrl` to: `https://abc123.ngrok.io/voice/webhook`

4. **Call the phone number** from Vapi dashboard!

---

## 🌐 Deploy Production

### Backend (Railway):
```bash
railway login
railway init
railway up
railway domain  # Get your URL
```

### Frontend (Vercel):
```bash
cd frontend
npm install
vercel
```

### Update .env:
```
BACKEND_URL=https://your-railway-url.up.railway.app
```

---

## 🧪 Run Evaluations

```bash
python scripts\eval_system.py
```

---

## 📝 What Sam Knows

Sam has been trained on:
- **Your Resume**: Education, experience, skills from Vaibhav_Pandey_Intern_Resume.pdf
- **GitHub Repos**:
  - meta-hackathon-incident-commander (Python, FastAPI, OpenEnv, SRE)
  - HotelBookingPro (TypeScript, JWT, hotel booking)
  - ideaspark-studio (TypeScript)
  - localo (TypeScript)
  - Email-Spam-Classifier (Python/ML)
  - ai-resume-analyzer1 (JavaScript)
  - Personal-Portfolio (TypeScript)

---

## 💬 Example Questions to Test

Try asking Sam:
- "What is Vaibhav's educational background?"
- "Tell me about the incident commander project"
- "What programming languages does Vaibhav know?"
- "Can you explain the HotelBookingPro architecture?"
- "Are you available next Tuesday at 2 PM?" (triggers calendar check)

---

## 🛠️ Troubleshooting

**"Vector store not found"**:
```bash
python scripts\ingest_data_groq.py
```

**"RAG system not initialized"**:
- Check that `chroma_db/` folder exists
- Re-run ingestion script

**Backend won't start**:
```bash
pip install fastapi uvicorn httpx chromadb sentence-transformers
```

**Voice agent not responding**:
- Verify ngrok is running
- Check Vapi dashboard serverUrl
- Look at backend console logs

---

## 🎯 Next Steps

1. ✅ Backend running locally
2. ⏳ Test chat API
3. ⏳ Setup ngrok for voice
4. ⏳ Deploy to Railway + Vercel
5. ⏳ Run evaluations
6. ⏳ Record Loom video
7. ⏳ Submit to Scaler

---

## 📊 Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Resume | ✅ Ready | 3518 chars ingested |
| GitHub | ✅ Ready | 7 repos, 24 docs, 63 chunks |
| Vector DB | ✅ Ready | ChromaDB with 63 chunks |
| RAG Engine | ✅ Ready | Groq Llama 3.1 70B |
| Calendar | ✅ Ready | Cal.com integrated |
| Voice | ⏳ Pending | Needs ngrok + Vapi update |
| Frontend | ⏳ Pending | Run `cd frontend && npm start` |

---

**Ready to go! Start the backend now.**
