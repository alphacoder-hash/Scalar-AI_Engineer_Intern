FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY chroma_db/ ./chroma_db/
COPY data/ ./data/
COPY start_server.py .
COPY .env.example .env

RUN mkdir -p evals

EXPOSE 8000

CMD ["python", "start_server.py"]
