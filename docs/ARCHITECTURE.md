# Architecture Deep Dive

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER LAYER                           │
│  ┌──────────────┐              ┌────────────────┐          │
│  │ Phone Call   │              │  Web Browser   │          │
│  │  (Voice)     │              │   (Chat UI)    │          │
│  └──────┬───────┘              └────────┬───────┘          │
└─────────┼──────────────────────────────┼──────────────────┘
          │                               │
┌─────────▼──────────────────────────────▼──────────────────┐
│                   INTERFACE LAYER                          │
│  ┌──────────────┐              ┌────────────────┐          │
│  │    Vapi      │              │   React SPA    │          │
│  │ (Orchestrator)│             │   Frontend     │          │
│  │              │              │                │          │
│  │ - Twilio     │              │ - Axios client │          │
│  │ - Deepgram   │              │ - Websocket    │          │
│  │ - ElevenLabs │              └────────┬───────┘          │
│  └──────┬───────┘                       │                  │
└─────────┼───────────────────────────────┼──────────────────┘
          │                               │
          │    Webhook / Function Call    │    HTTP/WS
          │                               │
┌─────────▼───────────────────────────────▼──────────────────┐
│                  BACKEND LAYER (FastAPI)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │              voice_handler.py                      │    │
│  │  - Handle Vapi webhooks                            │    │
│  │  - Route function calls                            │    │
│  │  - Log metrics                                     │    │
│  └──────┬─────────────────────────────────┬───────────┘    │
│         │                                  │                │
│  ┌──────▼─────────┐              ┌────────▼─────────┐     │
│  │  rag_engine.py │              │ calendar_manager │     │
│  │                │              │      .py         │     │
│  │ - Query RAG    │              │                  │     │
│  │ - Stream resp  │              │ - Check slots    │     │
│  │ - Memory mgmt  │              │ - Book meetings  │     │
│  └────────┬───────┘              └────────┬─────────┘     │
└───────────┼──────────────────────────────┼────────────────┘
            │                               │
┌───────────▼──────────────────────────────▼────────────────┐
│                    DATA LAYER                              │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────┐  │
│  │  ChromaDB   │   │  OpenAI API  │   │ Google Cal API│  │
│  │             │   │              │   │               │  │
│  │ - Embeddings│   │ - GPT-4o     │   │ - Free/busy   │  │
│  │ - Vector    │   │ - Embeddings │   │ - Booking     │  │
│  │   search    │   │              │   │               │  │
│  └─────────────┘   └──────────────┘   └───────────────┘  │
└────────────────────────────────────────────────────────────┘
```

## Voice Pipeline (Part A)

### Call Flow
1. **Incoming Call** → Twilio phone number
2. **Audio Stream** → Deepgram Nova-2 (STT)
3. **Text** → Vapi routes to backend webhook
4. **Function Call** → Backend executes (RAG query, calendar check)
5. **Response** → LLM (GPT-4o) generates answer
6. **Audio** → ElevenLabs (TTS)
7. **Stream** → Caller

### Latency Optimization
- **Deepgram Nova-2**: ~300ms STT
- **GPT-4o streaming**: ~500ms first token
- **ElevenLabs optimized**: ~200ms first audio byte
- **Total target**: < 1.5s first response

### Interrupt Handling
```python
# Vapi handles this automatically
"interruptionsEnabled": true
"backgroundSound": "off"
"backchannelingEnabled": false
```

## Chat Pipeline (Part B)

### Request Flow
1. **User message** → React frontend
2. **HTTP POST** → FastAPI `/chat` endpoint
3. **RAG Query**:
   - Embed query with OpenAI
   - Vector search in ChromaDB (top-k=5)
   - Retrieve relevant documents
4. **LLM Generation**:
   - Format prompt with context
   - Stream GPT-4o response
   - Save to conversation memory
5. **Response** → Frontend with sources

### RAG Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│ OpenAI Embeddings│
│ text-embed-3-sm  │
└────────┬─────────┘
         │ [768-dim vector]
         ▼
┌─────────────────┐
│   ChromaDB      │
│ Cosine similarity│
│   search k=5    │
└────────┬─────────┘
         │ [Retrieved docs]
         ▼
┌─────────────────┐
│  Context Builder│
│ - Resume chunks │
│ - GitHub docs   │
│ - Commit history│
└────────┬─────────┘
         │ [Combined context]
         ▼
┌─────────────────┐
│  Prompt Template│
│ System + Context│
│ + Chat History  │
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│   GPT-4o LLM    │
│ temp=0.3, stream│
└────────┬─────────┘
         │
         ▼
    Response
```

## Data Ingestion

### Sources
1. **Resume** (PDF/DOCX)
   - Parsed with pypdf/python-docx
   - Chunked with 1000 char chunks, 200 overlap
   
2. **GitHub Repos**
   - README files
   - Key config files (package.json, requirements.txt)
   - Recent commits (last 20)
   - Metadata preserved (repo name, URL, file path)

3. **Chunking Strategy**
   ```python
   RecursiveCharacterTextSplitter(
       chunk_size=1000,
       chunk_overlap=200,
       separators=["\n\n", "\n", " ", ""]
   )
   ```

## Calendar Integration

### Google Calendar Flow
1. OAuth 2.0 authentication (one-time)
2. Token stored in token.pickle
3. FreeBusy API query for availability
4. Event creation with email invites
5. Automatic reminders

### Slot Generation
- Working hours: 9 AM - 5 PM
- Weekdays only
- 30-minute slots
- Returns max 20 slots

## Evaluation Framework

### Voice Metrics
```python
- First response latency (avg, p95)
- Call success rate
- Booking completion rate
- Interruption handling
```

### Chat Metrics
```python
- Hallucination rate
- Retrieval precision/recall
- Response groundedness
- Rejection accuracy (when should say "don't know")
```

### Logging
- All calls logged to `evals/call_logs.jsonl`
- Metrics aggregated in `run_evals.py`
- Results saved to `evals/metrics.json`

## Security

1. **API Keys**: Environment variables only
2. **Webhook verification**: HMAC signature check
3. **Rate limiting**: FastAPI middleware
4. **Input sanitization**: Prompt injection detection
5. **Calendar**: OAuth with minimal scopes

## Scalability

### Current Setup (MVP)
- Single instance FastAPI
- ChromaDB local persistent
- ~100 concurrent chats
- ~10 concurrent calls (Vapi limit)

### Production Scale
- **Backend**: Horizontal scaling (load balancer)
- **Vector DB**: Pinecone cloud (managed)
- **Caching**: Redis for repeated queries
- **CDN**: Frontend on Vercel/Netlify edge

## Cost Analysis

### Per Voice Call (5 min avg)
- Twilio: $0.065
- Vapi: $0.25
- Deepgram: included in Vapi
- ElevenLabs: included in Vapi
- OpenAI GPT-4o: $0.02 (~2K tokens)
- **Total: $0.34/call**

### Per Chat Session (10 messages)
- OpenAI GPT-4o: $0.015 (~1.5K tokens)
- OpenAI embeddings: $0.0001
- ChromaDB: free (self-hosted)
- **Total: $0.016/session**

### Monthly (100 calls + 500 chats)
- Voice: $34
- Chat: $8
- Hosting: $20 (Railway/Render)
- **Total: ~$62/month**
