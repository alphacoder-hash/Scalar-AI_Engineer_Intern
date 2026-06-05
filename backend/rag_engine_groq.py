import os
import re
import json
import uuid
from typing import Dict, Optional, AsyncIterator, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
import chromadb
from sentence_transformers import SentenceTransformer

CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Vaibhav Pandey")

# ── Injection detection ───────────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|prior)\s+instructions?",
    r"forget\s+(everything|all|your instructions?)",
    r"(system|assistant)\s*:",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if\s+you\s+are|a\s+different|an?\s+)",
    r"you\s+are\s+now\s+",
    r"disregard\s+(all|your|previous)",
    r"new\s+(persona|role|identity)",
    r"\bdan\b.*mode",
    r"jailbreak",
    r"roleplay\s+as",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"what\s+(are\s+your|is\s+your)\s+(instructions?|prompt|system)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

REJECTION_RESPONSE = (
    f"I'm here to discuss {CANDIDATE_NAME}'s background and qualifications. "
    "Is there something about his skills, projects, or experience I can help with?"
)

# ── System prompts ────────────────────────────────────────────────────────────
SYSTEM_PROMPT_CHAT = """You are Sam, an AI persona representing {name} who is applying for an AI Engineer role at Scaler.

RETRIEVED CONTEXT (use ALL sources below — do not ignore any):
{context}

YOUR RULES:
1. Answer ONLY from the context above. If the answer is not there, say exactly: "I don't have that specific detail in my knowledge base — you can ask {name} directly during the interview."
2. NEVER invent, guess, or extrapolate facts.
3. For questions about a specific GitHub project, reference actual file names, functions, design decisions, or commit messages from the context.
4. For "why is he right for this role" — cite specific projects, stack choices, and measurable outcomes from the context.
5. For adversarial or off-topic questions (favourite colour, personal life, etc.) — stay professional: "That's outside what I can speak to — I'm here to represent {name}'s technical background."
6. Be conversational and specific. Avoid bullet-point dumps unless it genuinely aids clarity.
7. Give complete, evidence-backed answers for chat (this is NOT a voice call — you can use 2-4 paragraphs if the question warrants it).
8. Cite your source inline naturally: e.g. "According to his resume...", "The IncidentCommander README shows...", "A commit from March 2025 shows..."
"""

SYSTEM_PROMPT_VOICE = """You are Sam, an AI persona representing {name} for an AI Engineer role at Scaler.

CONTEXT:
{context}

RULES:
1. Answer ONLY from context. If not there: "I don't have that detail — ask {name} directly."
2. NEVER invent facts.
3. Keep answers to 2-3 sentences max — this is a phone call.
4. Be natural: "Sure!", "Great question", "Absolutely".
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
        self.sessions: Dict[str, List] = {}
        self._init_chroma()

    def _init_chroma(self):
        candidates = [
            os.getenv("CHROMA_PERSIST_DIR"),
            "/app/chroma_db",
            "chroma_db",
            os.path.join(os.getcwd(), "chroma_db"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db"),
        ]
        for persist_dir in filter(None, candidates):
            full_path = Path(persist_dir)
            print(f"Trying chroma path: {full_path} (exists: {full_path.exists()})")
            if full_path.exists():
                try:
                    client = chromadb.PersistentClient(path=str(full_path))
                    collections = client.list_collections()
                    if collections:
                        self.collection = client.get_collection(collections[0].name)
                        print(f"Vector store loaded: {full_path} ({self.collection.count()} chunks)")
                        return
                    else:
                        print(f"No collections in {full_path}")
                except Exception as e:
                    print(f"Failed to load from {full_path}: {e}")
        print(f"WARNING: Vector store not found. CWD: {os.getcwd()}")

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def _detect_repo_focus(self, query: str) -> Optional[str]:
        """If the query names a specific repo, return it for focused retrieval."""
        q = query.lower()
        known_repos = [
            "incidentcommander", "meta-hackathon-incident-commander",
            "hotelbookingpro", "email-spam-classifier",
            "ai-resume-analyzer", "personal-portfolio",
            "ideaspark-studio", "localo",
        ]
        for repo in known_repos:
            # match loose variants, e.g. "incident commander", "hotel booking"
            slug = repo.replace("-", "").replace("_", "").lower()
            if slug in q.replace(" ", "").replace("-", "").replace("_", ""):
                return repo
        return None

    def _retrieve(self, query: str, k: int = 8) -> List[Dict]:
        if not self.collection:
            return []

        embedding = self.encoder.encode([query])[0].tolist()
        total = self.collection.count()
        n_fetch = min(max(k * 3, 24), total)

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_fetch,
        )

        all_docs = []
        for i, doc in enumerate(results["documents"][0]):
            all_docs.append({
                "content": doc,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else 1.0,
            })

        # If query is about a specific repo, boost those docs to the front
        focused_repo = self._detect_repo_focus(query)
        if focused_repo:
            repo_slug = focused_repo.replace("-", "").replace("_", "").lower()
            priority, rest = [], []
            for doc in all_docs:
                repo_meta = doc["metadata"].get("repo", "").replace("-", "").replace("_", "").lower()
                if repo_slug in repo_meta or repo_meta in repo_slug:
                    priority.append(doc)
                else:
                    rest.append(doc)
            all_docs = priority + rest

        # Diversify: no more than 2 chunks from same (source, repo, type) triple
        counts: Dict[str, int] = {}
        diverse = []
        for doc in all_docs:
            m = doc["metadata"]
            key = f"{m.get('source','')}:{m.get('repo','')}:{m.get('type','')}"
            if counts.get(key, 0) < 2:
                diverse.append(doc)
                counts[key] = counts.get(key, 0) + 1
            if len(diverse) >= k:
                break

        return diverse[:k]

    # ── Session history ───────────────────────────────────────────────────────

    def _get_history(self, session_id: str) -> List:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    # ── Message building ──────────────────────────────────────────────────────

    def _build_context(self, docs: List[Dict]) -> str:
        parts = []
        for d in docs:
            m = d["metadata"]
            label = f"[source={m.get('source','?')} | repo={m.get('repo','')} | file={m.get('file','')} | type={m.get('type','')}]"
            parts.append(f"{label}\n{d['content']}")
        return "\n\n---\n\n".join(parts)

    def _build_messages(self, question: str, docs: List[Dict], history: List,
                        voice: bool = False) -> List[Dict]:
        context = self._build_context(docs)
        template = SYSTEM_PROMPT_VOICE if voice else SYSTEM_PROMPT_CHAT
        system = template.format(name=CANDIDATE_NAME, context=context)

        messages = [{"role": "system", "content": system}]
        for human, ai in history[-6:]:
            messages.append({"role": "user", "content": human})
            messages.append({"role": "assistant", "content": ai})
        messages.append({"role": "user", "content": question})
        return messages

    # ── Public API ────────────────────────────────────────────────────────────

    async def query(self, message: str, session_id: Optional[str] = None,
                    voice: bool = False) -> Dict:
        if session_id is None:
            session_id = str(uuid.uuid4())

        if not self.collection:
            return {
                "answer": "Knowledge base not ready. Run: python scripts/ingest_data_groq.py",
                "session_id": session_id,
                "sources": [],
            }

        if _INJECTION_RE.search(message):
            return {"answer": REJECTION_RESPONSE, "session_id": session_id, "sources": []}

        docs = self._retrieve(message)
        history = self._get_history(session_id)
        messages = self._build_messages(message, docs, history, voice=voice)
        max_tokens = 200 if voice else 600

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.groq_url,
                headers={"Authorization": f"Bearer {self.groq_api_key}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages,
                      "max_tokens": max_tokens, "temperature": 0.3},
                timeout=30.0,
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]

        history.append((message, answer))
        return {"answer": answer, "session_id": session_id, "sources": docs}

    async def query_stream(self, message: str, session_id: Optional[str] = None) -> AsyncIterator[Dict]:
        if session_id is None:
            session_id = str(uuid.uuid4())

        if not self.collection:
            yield {"type": "error", "content": "RAG system not initialized"}
            return

        if _INJECTION_RE.search(message):
            yield {"type": "content", "content": REJECTION_RESPONSE, "session_id": session_id}
            yield {"type": "sources", "sources": [], "session_id": session_id}
            return

        docs = self._retrieve(message)
        history = self._get_history(session_id)
        messages = self._build_messages(message, docs, history, voice=False)

        full_response = ""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                self.groq_url,
                headers={"Authorization": f"Bearer {self.groq_api_key}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages,
                      "max_tokens": 600, "temperature": 0.3, "stream": True},
                timeout=30.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        delta = data["choices"][0]["delta"].get("content", "")
                        if delta:
                            full_response += delta
                            yield {"type": "content", "content": delta, "session_id": session_id}

        history.append((message, full_response))
        yield {"type": "sources", "sources": docs, "session_id": session_id}

    def is_ready(self) -> bool:
        return self.collection is not None
