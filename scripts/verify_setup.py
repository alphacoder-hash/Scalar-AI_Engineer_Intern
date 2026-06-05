"""
Verify the full project setup is correct before running.
Usage: python scripts/verify_setup.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

passed = failed = 0

def ok(msg):
    global passed
    passed += 1
    print(f"  ✅ {msg}")

def fail(msg):
    global failed
    failed += 1
    print(f"  ❌ {msg}")

def warn(msg):
    print(f"  ⚠️  {msg}")

print("=" * 55)
print("  Sam — Setup Verification")
print("=" * 55)

# ── Files ──────────────────────────────────────────────────────────────────────
print("\n📁 Core files:")
REQUIRED_FILES = [
    ("backend/app.py",              "Backend API"),
    ("backend/rag_engine_groq.py",  "RAG Engine (Groq)"),
    ("backend/calendar_calcom.py",  "Calendar (Cal.com)"),
    ("backend/voice_handler.py",    "Voice Handler"),
    ("scripts/ingest_data_groq.py", "Data Ingestion"),
    ("scripts/setup_vapi.py",       "Vapi Setup"),
    ("frontend/src/App.js",         "Frontend"),
    ("requirements.txt",            "Python deps"),
    ("README.md",                   "Docs"),
]
root = Path(__file__).parent.parent
for rel, desc in REQUIRED_FILES:
    if (root / rel).exists():
        ok(desc)
    else:
        fail(f"{desc} — {rel} NOT FOUND")

# ── Env vars ───────────────────────────────────────────────────────────────────
print("\n🔐 Environment variables:")
ENV_REQUIRED = [
    ("GROQ_API_KEY",    "Groq API key (chat LLM)"),
    ("VAPI_API_KEY",    "Vapi API key (voice)"),
    ("CALCOM_API_KEY",  "Cal.com API key (booking)"),
    ("GITHUB_TOKEN",    "GitHub token (ingestion)"),
    ("GITHUB_USERNAME", "GitHub username"),
]
ENV_OPTIONAL = [
    ("VAPI_SERVER_SECRET", "Vapi webhook secret (recommended)"),
    ("CALCOM_USERNAME",    "Cal.com username"),
    ("BACKEND_URL",        "Backend URL (Railway)"),
]
for var, desc in ENV_REQUIRED:
    val = os.getenv(var)
    if val:
        masked = val[:8] + "..." if len(val) > 8 else "***"
        ok(f"{desc}: {masked}")
    else:
        fail(f"{desc}: {var} not set")

for var, desc in ENV_OPTIONAL:
    val = os.getenv(var)
    if val:
        ok(f"{desc}: set")
    else:
        warn(f"{desc}: {var} not set (optional)")

# ── Resume ─────────────────────────────────────────────────────────────────────
print("\n📄 Data sources:")
resume = os.getenv("RESUME_PATH", "./data/Vaibhav_Pandey_Intern_Resume.pdf")
if (root / resume.lstrip("./")).exists() or Path(resume).exists():
    ok(f"Resume found: {resume}")
else:
    fail(f"Resume NOT found: {resume}")

# ── ChromaDB ───────────────────────────────────────────────────────────────────
print("\n🗄️  Vector store:")
chroma = Path(os.getenv("CHROMA_PERSIST_DIR", "chroma_db"))
if not chroma.is_absolute():
    chroma = root / chroma
sqlite = chroma / "chroma.sqlite3"
has_parquet = any(chroma.rglob("*.parquet")) if chroma.exists() else False

if chroma.exists() and sqlite.exists() and has_parquet:
    ok(f"ChromaDB ready at {chroma}")
elif chroma.exists() and sqlite.exists():
    warn("ChromaDB directory exists but no parquet files — may be empty. Run ingest_data_groq.py")
else:
    fail("ChromaDB not found — run: python scripts/ingest_data_groq.py")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print(f"  {passed} passed  |  {failed} failed")
print("=" * 55)

if failed == 0:
    print("\n✅ All checks passed!\n")
    print("Next steps:")
    print("  1. python scripts/ingest_data_groq.py   # if ChromaDB is empty")
    print("  2. python scripts/setup_vapi.py         # voice agent")
    print("  3. cd backend && uvicorn app:app --reload")
    print("  4. cd frontend && npm start")
else:
    print(f"\n❌ {failed} check(s) failed — fix above before running.\n")
    sys.exit(1)
