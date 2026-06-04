#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def ingest_if_needed():
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    chroma_path = Path(persist_dir)
    
    # Check if vector store already has data
    if chroma_path.exists() and any(chroma_path.glob("**/*.bin")):
        print("Vector store found, skipping ingestion.")
        return True
    
    print("Vector store not found. Running data ingestion...")
    
    # Set PYTHONIOENCODING for subprocess
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    result = subprocess.run(
        [sys.executable, "scripts/ingest_data_groq.py"],
        cwd=Path(__file__).parent,
        env=env
    )
    
    if result.returncode != 0:
        print("WARNING: Data ingestion failed. Starting server anyway...")
        return False
    
    print("Data ingestion complete!")
    return True

if __name__ == "__main__":
    ingest_if_needed()
    
    port = os.getenv("PORT", "8000")
    print(f"Starting server on port {port}...")
    
    os.execvp(sys.executable, [
        sys.executable, "-m", "uvicorn",
        "backend.app:app",
        "--host", "0.0.0.0",
        "--port", port
    ])
