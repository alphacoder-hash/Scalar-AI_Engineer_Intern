import os
import sys
from pathlib import Path

def check_file(path, description):
    """Check if file exists"""
    if Path(path).exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} NOT FOUND")
        return False

def check_env_var(var, description):
    """Check if environment variable is set"""
    if os.getenv(var):
        print(f"✅ {description}: {var} is set")
        return True
    else:
        print(f"⚠️  {description}: {var} not set")
        return False

def main():
    print("=== AI Persona Setup Verification ===\n")
    
    checks_passed = 0
    checks_total = 0
    
    print("📁 File Structure:")
    files = [
        ("backend/app.py", "Backend API"),
        ("backend/rag_engine.py", "RAG Engine"),
        ("backend/calendar_manager.py", "Calendar Manager"),
        ("backend/voice_handler.py", "Voice Handler"),
        ("scripts/ingest_data.py", "Data Ingestion"),
        ("scripts/setup_vapi.py", "Vapi Setup"),
        ("frontend/src/App.js", "Frontend App"),
        ("requirements.txt", "Python Dependencies"),
        ("README.md", "Documentation"),
    ]
    
    for path, desc in files:
        checks_total += 1
        if check_file(path, desc):
            checks_passed += 1
    
    print("\n🔐 Environment Variables:")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = [
        ("OPENAI_API_KEY", "OpenAI API Key"),
        ("VAPI_API_KEY", "Vapi API Key"),
        ("GITHUB_USERNAME", "GitHub Username"),
    ]
    
    for var, desc in env_vars:
        checks_total += 1
        if check_env_var(var, desc):
            checks_passed += 1
    
    print("\n📊 Data Sources:")
    checks_total += 1
    resume_path = os.getenv("RESUME_PATH", "./data/resume.pdf")
    if check_file(resume_path, "Resume"):
        checks_passed += 1
    
    print("\n🗄️ Vector Store:")
    checks_total += 1
    if check_file("./chroma_db", "ChromaDB"):
        checks_passed += 1
    else:
        print("   Run: python scripts/ingest_data.py")
    
    print("\n" + "="*50)
    print(f"Status: {checks_passed}/{checks_total} checks passed")
    
    if checks_passed == checks_total:
        print("\n✅ Setup complete! Ready to run.\n")
        print("Next steps:")
        print("1. cd backend && uvicorn app:app --reload")
        print("2. cd frontend && npm start")
        print("3. python scripts/setup_vapi.py")
    else:
        print("\n⚠️  Some checks failed. Review SETUP.md\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
