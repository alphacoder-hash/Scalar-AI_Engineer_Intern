# TODO — End-to-end AI Persona (Voice + Chat + Evals)

- [ ] Implement plan: refactor `/chat` booking autonomy to structured extraction + slot identifiers (remove brittle heuristics)
- [ ] Add/align JSONL logging for chat booking attempts (so evals can compute booking success)
- [ ] Fix eval ingestion mismatch: `scripts/eval_system.py` ↔ `backend/voice_handler.py` log schema (latency/duration + booking success)
- [ ] Ensure PDF report generation reflects updated metrics
- [ ] Run ingestion + start backend/frontend + run smoke tests (voice booking via Vapi + chat booking via /chat)
- [ ] Run evals end-to-end and generate `evals/report.pdf`

