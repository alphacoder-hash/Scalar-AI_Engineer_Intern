import os
import sys
from dotenv import load_dotenv

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

print("="*60)
print("   Configuration Check for Sam")
print("="*60)

checks = {
    "Groq API Key": os.getenv("GROQ_API_KEY"),
    "Vapi API Key": os.getenv("VAPI_API_KEY"),
    "GitHub Token": os.getenv("GITHUB_TOKEN"),
    "GitHub Username": os.getenv("GITHUB_USERNAME"),
    "Cal.com API Key": os.getenv("CALCOM_API_KEY"),
    "Cal.com Username": os.getenv("CALCOM_USERNAME"),
    "Candidate Name": os.getenv("CANDIDATE_NAME"),
    "Resume Path": os.getenv("RESUME_PATH")
}

all_good = True

for name, value in checks.items():
    if value:
        # Mask sensitive data
        if "Key" in name or "Token" in name:
            display = value[:8] + "..." if len(value) > 8 else "***"
        else:
            display = value
        print(f"✓ {name}: {display}")
    else:
        print(f"❌ {name}: NOT SET")
        all_good = False

print("\n" + "="*60)

# Check resume file
resume_path = os.getenv("RESUME_PATH", "./data/resume.pdf")
if os.path.exists(resume_path):
    print(f"✓ Resume file found: {resume_path}")
else:
    print(f"❌ Resume file NOT FOUND: {resume_path}")
    all_good = False

# Check if vector store exists
if os.path.exists("./chroma_db"):
    print("✓ Vector store exists (data already ingested)")
else:
    print("⚠ Vector store NOT found (run: python scripts/ingest_data_groq.py)")
    all_good = False

print("="*60)

if all_good:
    print("\n✅ All checks passed! Ready to run.")
    print("\nNext steps:")
    print("1. Run: python scripts/ingest_data_groq.py")
    print("2. Run: cd backend && python -m uvicorn app:app --reload")
    print("3. Test: http://localhost:8000/health")
else:
    print("\n❌ Some checks failed. Fix the issues above.")
