"""
DEPRECATED — this script used OpenAI embeddings and LangChain.

Use the correct ingestion script instead:
    python scripts/ingest_data_groq.py

That script uses:
  - sentence-transformers/all-MiniLM-L6-v2  (local, free)
  - ChromaDB v0.4+                           (local, free)
  - PyGithub                                 (GitHub API)
  - pypdf                                    (PDF parsing)
"""
import sys
print("ERROR: ingest_data.py is deprecated.")
print("Run:  python scripts/ingest_data_groq.py")
sys.exit(1)
