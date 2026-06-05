"""
Quick configuration check for Sam.
Usage: python scripts/check_setup.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")

print("=" * 60)
print("   Configuration Check — Sam (Vaibhav Pandey AI Persona)")
print("=" * 60)

checks = {
    "Groq API Key":     os.getenv("GROQ_API_KEY"),
    "Vapi API Key":     os.getenv("VAPI_API_KEY"),
    "Cal.com API Key":  os.getenv("CALCOM_API_KEY"),
    "Cal.com Username": os.getenv("CALCOM_USERNAME"),
    "GitHub Token":     os.getenv("GITHUB_TOKEN"),
    "GitHub Username":  os.getenv("GITHUB_USERNAME"),
    "Candidate Name":   os.getenv("CANDIDATE_NAME"),
    "Resume Path":      os.getenv("RESUME_PATH"),
    "Backend URL":      os.getenv("BACKEND_URL"),
}

all_good = True
for name, value in checks.items():
    if value:
        display = (value[:8] + "...") if ("Key" in name or "Token" in name) and len(value) > 8 else value
        print(f"  ✅ {name}: {display}")
    else:
        print(f"  ❌ {name}: NOT SET")
        if name not in ("Backend URL",):  # optional for local dev
            all_good = False

print("\n" + "=" * 60)

# Resume
resume_path = os.getenv("RESUME_PATH", "./data/Vaibhav_Pandey_Intern_Resume.pdf")
root = Path(__file__).parent.parent
resolved = (root / resume_path.lstrip("./")) if not Path(resume_path).is_absolute() else Path(resume_path)
if resolved.exists():
    print(f"  ✅ Resume file found: {resume_path}")
else:
    print(f"  ❌ Resume NOT found: {resume_path}")
    all_good = False

# ChromaDB — v0.4+ uses sqlite3 + parquet, not .bin
chroma_dir = Path(os.getenv("CHROMA_PERSIST_DIR", "chroma_db"))
if not chroma_dir.is_absolute():
    chroma_dir = root / chroma_dir
if chroma_dir.exists() and (chroma_dir / "chroma.sqlite3").exists() and any(chroma_dir.rglob("*.parquet")):
    print("  ✅ ChromaDB vector store ready")
else:
    print("  ⚠️  ChromaDB not ready — run: python scripts/ingest_data_groq.py")

print("=" * 60)

if all_good:
    print("\n✅ Configuration looks good!\n")
    print("Run order:")
    print("  1. python scripts/ingest_data_groq.py")
    print("  2. python scripts/setup_vapi.py")
    print("  3. cd backend && uvicorn app:app --reload")
    print("  4. cd frontend && npm start")
else:
    print("\n❌ Some required variables are missing. Check .env\n")
