#!/usr/bin/env python3
"""
Startup script for Railway deployment.
Auto-ingests data if vector store is missing, then starts the server.
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def ingest_if_needed():
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    chroma_path = Path(persist_dir)
    
    if chroma_path.exists() and any(chroma_path.iterdir()):
        print("Vector store found, skipping ingestion.")
        return
    
    print("Vector store not found. Running data ingestion...")
    result = subprocess.run(
        [sys.executable, "scripts/ingest_data_groq.py"],
        cwd=Path(__file__).parent
    )
    
    if result.returncode != 0:
        print("WARNING: Data ingestion failed. Starting anyway...")

if __name__ == "__main__":
    ingest_if_needed()
    
    port = os.getenv("PORT", "8000")
    os.execvp(sys.executable, [
        sys.executable, "-m", "uvicorn",
        "backend.app:app",
        "--host", "0.0.0.0",
        "--port", port
    ])
