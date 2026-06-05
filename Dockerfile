FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY chroma_db/ ./chroma_db/
COPY data/ ./data/
COPY start_server.py .

ENV PYTHONPATH=/app
ENV CHROMA_PERSIST_DIR=/app/chroma_db
# Pre-download embedding model so startup doesn't time out
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

EXPOSE 8000

CMD python -m uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}
