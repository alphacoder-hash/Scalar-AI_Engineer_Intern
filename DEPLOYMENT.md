# Deployment Guide

## Quick Start

### 1. Prerequisites
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
cd frontend && npm install
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Prepare Data
```bash
# Add your resume to data/resume.pdf
# Set GITHUB_USERNAME and GITHUB_REPOS in .env

# Run ingestion
python scripts/ingest_data.py
```

### 4. Setup Vapi Voice Agent
```bash
# Configure Vapi assistant
python scripts/setup_vapi.py
```

### 5. Run Backend
```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 6. Run Frontend
```bash
cd frontend
npm start
```

## Production Deployment

### Backend (Railway/Render/Fly.io)

**Railway:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY scripts/ ./scripts/

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Vercel/Netlify)

**Vercel:**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel
```

**netlify.toml:**
```toml
[build]
  command = "npm run build"
  publish = "build"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### Vapi Configuration

1. Go to https://vapi.ai
2. Sign up and get API key
3. Run `python scripts/setup_vapi.py`
4. Update serverUrl in Vapi dashboard to your backend URL
5. Note your phone number

### Google Calendar Setup

1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Download credentials.json
6. Run backend once to authenticate
7. Token will be saved for future use

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
VAPI_API_KEY=...
GITHUB_USERNAME=your-username

# Optional
VAPI_SERVER_SECRET=random-secret
GOOGLE_CALENDAR_CREDENTIALS=./credentials.json
BACKEND_URL=https://your-backend.com
GITHUB_REPOS=repo1,repo2
```

## Testing

```bash
# Run evaluations
python scripts/run_evals.py

# Test voice
# Call the Vapi phone number

# Test chat
# Open http://localhost:3000
```

## Monitoring

- Voice calls: Check Vapi dashboard
- API logs: Backend console
- Call metrics: `evals/call_logs.jsonl`
- Eval results: `evals/metrics.json`

## Troubleshooting

**Vector store not found:**
```bash
python scripts/ingest_data.py
```

**Google Calendar auth:**
```bash
rm token.pickle
# Restart backend to re-authenticate
```

**Vapi webhook not working:**
- Ensure backend URL is publicly accessible
- Check serverUrlSecret matches
- Verify webhook endpoint: /voice/webhook
```
