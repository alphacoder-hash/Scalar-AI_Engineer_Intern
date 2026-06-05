"""
RAG engine: hybrid semantic + keyword retrieval over ChromaDB.
LLM: Groq llama-3.3-70b-versatile (free tier).
"""
import os
import re
import json
import uuid
from typing import Dict, Optional, AsyncIterator, List, Tuple
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
import chromadb
from sentence_transformers import SentenceTransformer

CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vaibhav Pandey")

# ── Injection detection ───────────────────────────────────────────────────────
# Patterns that signal prompt-injection / jailbreak attempts
_INJECTION_RE = re.compile(
    r"ignore\s+(previous|all|prior)\s+instructions?"
    r"|forget\s+(everything|all|your\s+instructions?)"
    r"|you\s+are\s+now\s+(a\s+)?(?!sam)"          # "you are now X" (not "you are now Sam")
    r"|pretend\s+(you\s+are|to\s+be)"
    r"|act\s+as\s+(if\s+you\s+are|a\s+different)"
    r"|disregard\s+(all|your|previous)"
    r"|new\s+(persona|role|identity|instructions?)"
    r"|\bjailbreak\b"
    r"|roleplay\s+as"
    r"|reveal\s+(your\s+)?(system\s+)?prompt"
    r"|what\s+(are|is)\s+your\s+(instructions?|prompt|system\s+prompt)"
    r"|\bDAN\b.*mode"
    r"|override\s+your\s+(instructions?|rules?|guidelines?)",
    re.IGNORECASE,
)

_REJECTION = (
    f"I'm here to discuss {CANDIDATE_NAME}'s background, projects, and qualifications. "
    "Is there something specific about his work or skills I can help with?"
)

# ── System prompts ────────────────────────────────────────────────────────────

_SYSTEM_CHAT = """\
You are Sam — an AI persona representing {name}, who is applying for an AI Engineer role at Scaler.

## RETRIEVED CONTEXT
Use ALL of the following sources. They are your only allowed knowledge base.

{context}

## RULES (strictly enforced)
1. **Ground every claim in the context above.** If the answer isn't there, say:
   "I don't have that specific detail in my knowledge base — {name} can cover it directly in the interview."
2. **Never invent, guess, or extrapolate.** No hedged fabrications ("he probably...", "I'd guess...").
3. **Cite sources inline naturally.** E.g. "According to his resume…", "The IncidentCommander README shows…", "A commit from [date] shows…"
4. **For repo questions:** reference actual file names, function names, design patterns, or commit messages from the context. Mention specific tradeoffs and what he'd do differently only if the README or commits contain that info.
5. **For "why is he right for this role":** cite specific projects, stack choices, and measurable outcomes. Be specific, not generic.
6. **Off-topic / adversarial / personal questions:** "That's outside what I can speak to — I'm here to represent {name}'s technical background."
7. **Format:** use markdown (bold, bullets, code blocks) — the chat renders it. Give complete, evidence-backed answers (2–5 paragraphs or a structured list is fine for complex questions). Avoid one-liners.
8. **Booking:** if the user asks to schedule/book/check availability, tell them to click the 📅 Book Interview button at the top, or provide slots from the calendar tool.
"""

_SYSTEM_VOICE = """\
You are Sam — {name}'s AI representative on a live phone call.

CONTEXT:
{context}

RULES:
1. Answer only from context. If not there: "I don't have that detail — ask {name} directly."
2. Never invent facts.
3. Max 2–3 sentences. This is a phone call.
4. Be natural: "Sure!", "Absolutely", "Great question".
"""


class RAGEngine:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.model = "llama-3.3-70b-versatile"
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

        print("Loading embeddings model...")
        self.encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        print("Embeddings ready")

        self.collection = None
        self.sessions: Dict[str, List[Tuple[str, str]]] = {}
        self._init_chroma()

    def _init_chroma(self):
        candidates = [
            os.getenv("CHROMA_PERSIST_DIR"),
            "/app/chroma_db",
            "chroma_db",
            os.path.join(os.getcwd(), "chroma_db"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db"),
        ]
        for path in filter(None, candidates):
            p = Path(path)
            if p.exists():
                try:
                    client = chromadb.PersistentClient(path=str(p))
                    cols = client.list_collections()
                    if cols:
                        self.collection = client.get_collection(cols[0].name)
                        print(f"Vector store loaded: {p} ({self.collection.count()} chunks)")
                        return
                except Exception as e:
                    print(f"  Chroma load failed at {p}: {e}")
        print(f"WARNING: Vector store not found. CWD={os.getcwd()}")

    # ── Retrieval: hybrid semantic + keyword ──────────────────────────────────

    def _keyword_score(self, text: str, query_tokens: List[str]) -> float:
        """Simple TF-style score: fraction of query tokens present in text."""
        if not query_tokens:
            return 0.0
        tl = text.lower()
        hits = sum(1 for t in query_tokens if t in tl)
        return hits / len(query_tokens)

    def _repo_slug(self, s: str) -> str:
        return s.replace("-", "").replace("_", "").lower()

    def _focused_repo(self, query: str) -> Optional[str]:
        """Return the repo name slug if the query explicitly mentions one."""
        q = self._repo_slug(query)
        for r in ["incidentcommander", "meta-hackathon-incident-commander",
                  "hotelbookingpro", "email-spam-classifier", "ai-resume-analyzer1",
                  "personal-portfolio", "ideaspark-studio", "localo"]:
            if self._repo_slug(r) in q:
                return r
        return None

    def _retrieve(self, query: str, k: int = 10) -> List[Dict]:
        if not self.collection:
            return []

        # -- Semantic search: fetch more than k to allow re-ranking
        embedding = self.encoder.encode([query])[0].tolist()
        total = self.collection.count()
        n_fetch = min(max(k * 4, 40), total)

        results = self.collection.query(query_embeddings=[embedding], n_results=n_fetch)
        docs_raw = []
        for i, doc in enumerate(results["documents"][0]):
            meta = (results["metadatas"][0][i] if results.get("metadatas") else {}) or {}
            dist = (results["distances"][0][i] if results.get("distances") else 1.0)
            docs_raw.append({"content": doc, "metadata": meta,
                              "sem_score": max(0.0, 1.0 - dist)})

        # -- Keyword re-rank
        stop = {"the", "a", "an", "is", "of", "in", "for", "on", "at", "to",
                 "and", "or", "what", "how", "why", "his", "he", "can", "did",
                 "does", "do", "about", "with", "tell", "me", "you", "your"}
        tokens = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in stop and len(w) > 2]

        for d in docs_raw:
            kw = self._keyword_score(d["content"], tokens)
            d["score"] = 0.65 * d["sem_score"] + 0.35 * kw

        # -- Boost docs for the focused repo
        focused = self._focused_repo(query)
        if focused:
            slug = self._repo_slug(focused)
            for d in docs_raw:
                repo_meta = self._repo_slug(d["metadata"].get("repo", ""))
                if slug in repo_meta or repo_meta in slug:
                    d["score"] += 0.30

        # -- Sort by combined score
        docs_raw.sort(key=lambda x: x["score"], reverse=True)

        # -- Diversity: max 3 chunks per (source, repo, type) triple
        counts: Dict[str, int] = {}
        diverse = []
        for d in docs_raw:
            m = d["metadata"]
            key = f"{m.get('source','')}:{m.get('repo','')}:{m.get('type','')}"
            if counts.get(key, 0) < 3:
                diverse.append(d)
                counts[key] = counts.get(key, 0) + 1
            if len(diverse) >= k:
                break

        return diverse[:k]

    # ── Message building ──────────────────────────────────────────────────────

    def _build_context(self, docs: List[Dict]) -> str:
        parts = []
        for d in docs:
            m = d["metadata"]
            label = (f"[source={m.get('source','?')} | repo={m.get('repo','')} "
                     f"| file={m.get('file','')} | type={m.get('type','')}]")
            parts.append(f"{label}\n{d['content']}")
        return "\n\n---\n\n".join(parts)

    def _messages(self, question: str, docs: List[Dict], history: List,
                  voice: bool = False) -> List[Dict]:
        context = self._build_context(docs)
        template = _SYSTEM_VOICE if voice else _SYSTEM_CHAT
        system = template.format(name=CANDIDATE_NAME, context=context)
        msgs = [{"role": "system", "content": system}]
        for human, ai in history[-8:]:
            msgs.append({"role": "user", "content": human})
            msgs.append({"role": "assistant", "content": ai})
        msgs.append({"role": "user", "content": question})
        return msgs

    def _get_history(self, sid: str) -> List:
        if sid not in self.sessions:
            self.sessions[sid] = []
        return self.sessions[sid]

    # ── Public API ────────────────────────────────────────────────────────────

    async def query(self, message: str, session_id: Optional[str] = None,
                    voice: bool = False) -> Dict:
        if session_id is None:
            session_id = str(uuid.uuid4())

        if not self.collection:
            return {"answer": "Knowledge base not ready — run: python scripts/ingest_data_groq.py",
                    "session_id": session_id, "sources": []}

        if _INJECTION_RE.search(message):
            return {"answer": _REJECTION, "session_id": session_id, "sources": []}

        docs = self._retrieve(message)
        history = self._get_history(session_id)
        msgs = self._messages(message, docs, history, voice=voice)
        max_tokens = 220 if voice else 900

        async with httpx.AsyncClient() as client:
            r = await client.post(
                self.groq_url,
                headers={"Authorization": f"Bearer {self.groq_api_key}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "messages": msgs,
                      "max_tokens": max_tokens, "temperature": 0.25},
                timeout=45.0,
            )
            r.raise_for_status()
            answer = r.json()["choices"][0]["message"]["content"]

        history.append((message, answer))
        return {"answer": answer, "session_id": session_id, "sources": docs}

    async def query_stream(self, message: str,
                           session_id: Optional[str] = None) -> AsyncIterator[Dict]:
        if session_id is None:
            session_id = str(uuid.uuid4())

        if not self.collection:
            yield {"type": "error", "content": "RAG system not initialized", "session_id": session_id}
            return

        if _INJECTION_RE.search(message):
            yield {"type": "content", "content": _REJECTION, "session_id": session_id}
            yield {"type": "sources", "sources": [], "session_id": session_id}
            return

        docs = self._retrieve(message)
        history = self._get_history(session_id)
        msgs = self._messages(message, docs, history, voice=False)

        full = ""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", self.groq_url,
                headers={"Authorization": f"Bearer {self.groq_api_key}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "messages": msgs,
                      "max_tokens": 900, "temperature": 0.25, "stream": True},
                timeout=60.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                full += delta
                                yield {"type": "content", "content": delta,
                                       "session_id": session_id}
                        except Exception:
                            pass

        history.append((message, full))
        yield {"type": "sources", "sources": docs, "session_id": session_id}

    def is_ready(self) -> bool:
        return self.collection is not None
