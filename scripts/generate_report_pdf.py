import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def wrap_text(text: str, max_width_chars: int = 95):
    text = (text or "").strip()
    if not text:
        return []
    lines = []
    current = ""
    for word in text.split():
        if len(current) + len(word) + 1 <= max_width_chars:
            current = f"{current} {word}".strip()
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def main(metrics_path: str = "./evals/metrics.json", out_pdf: str = "./evals/report.pdf"):
    metrics_file = Path(metrics_path)
    if not metrics_file.exists():
        raise SystemExit(f"Missing metrics file: {metrics_path}. Run scripts/run_evals.py first.")

    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    voice = metrics.get("voice", {})
    chat = metrics.get("chat", {})
    ts = metrics.get("timestamp") or datetime.now().isoformat()

    Path(out_pdf).parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(out_pdf, pagesize=letter)
    width, height = letter

    x = 0.6 * inch
    y = height - 0.7 * inch
    line_h = 0.14 * inch

    def draw_heading(text):
        nonlocal y
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y, text)
        y -= line_h * 1.1

    def draw_bold(text):
        nonlocal y
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x, y, text)
        y -= line_h

    def draw_paragraph(text):
        nonlocal y
        c.setFont("Helvetica", 10)
        for line in wrap_text(text, max_width_chars=95):
            if y < 0.6 * inch:
                break
            c.drawString(x, y, line)
            y -= line_h

    draw_heading("AI Persona Evals Report (Voice + Chat)")
    draw_paragraph(f"Generated: {ts}")
    y -= 0.05 * inch

    # Executive summary
    draw_bold("Executive Summary")
    draw_paragraph(
        "Voice-first phone agent and chat agent use the same RAG knowledge base (resume + GitHub corpus). "
        "This run generated chat groundedness metrics and retrieval metrics; voice booking metrics require real call logging (evals/call_logs.jsonl)."
    )

    # Voice quality
    draw_bold("Part A: Voice Quality")
    if voice:
        total_calls = voice.get("total_calls", 0)
        draw_paragraph(
            f"Total calls logged: {total_calls}. "
            f"Avg first response latency: {voice.get('avg_latency', 0):.2f}s. "
            f"P95 latency: {voice.get('p95_latency', 0):.2f}s. "
            f"Booking success rate: {voice.get('success_rate', 0)*100:.1f}%."
        )
    else:
        draw_paragraph("No voice call logs found (evals/call_logs.jsonl). Run test calls via the Vapi phone number to populate logs.")

    # Chat groundedness
    draw_bold("Part B: Chat Groundedness")
    if chat:
        draw_paragraph(
            f"Total questions: {chat.get('total_questions', 0)}. "
            f"Hallucination rate: {chat.get('hallucination_rate', 0)*100:.1f}%. "
            f"Accuracy (answer or correct rejection): {chat.get('accuracy', 0)*100:.1f}%."
        )
    else:
        draw_paragraph("No chat groundedness metrics found.")

    # Retrieval quality (optional)
    draw_bold("Retrieval Quality")
    # We don't currently store precision/recall separately in metrics.json in this repo; keep placeholder.
    draw_paragraph(
        "This repo's run_evals.py prints retrieval precision/recall to stdout. "
        "If you want these persisted into metrics.json, update scripts/run_evals.py accordingly."
    )

    # Failure modes (template-friendly)
    draw_bold("Failure Modes Found (Template)")
    draw_paragraph(
        "1) If calendar tooling is missing/unauthenticated, booking confirmations can fall back or fail. Fix: ensure CALCOM_API_KEY/Google auth are configured and webhook parsing is strict.\n"
        "2) If retrieval returns low-confidence docs, the persona should say it lacks the information and ask during the interview. Fix: tighten groundedness prompt + retrieval confidence checks.\n"
        "3) Prompt injection attempts should not override system instructions. Fix: detect injection patterns and force a grounded refusal."
    )

    # Tradeoff
    draw_bold("Conscious Tradeoff")
    draw_paragraph(
        "Speed vs perfect accuracy: the system streams chat responses and keeps temperature low to reduce hallucination risk while maintaining low latency for screening UX."
    )

    # Future 2 weeks
    draw_bold("What I'd Build in 2 More Weeks")
    draw_paragraph(
        "- Automated end-to-end test harness that drives voice and chat scenarios and measures booking success.\n"
        "- Persistent retrieval precision/recall and a judge-based hallucination grader with labeled evidence.\n"
        "- Stronger structured extraction for booking (datetime/name/email) with validation + retry loops."
    )

    c.showPage()
    c.save()
    print(f"✅ Wrote {out_pdf}")


if __name__ == "__main__":
    main()

