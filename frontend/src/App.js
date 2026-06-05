import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const PHONE_NUMBER = process.env.REACT_APP_PHONE_NUMBER || '';

// ── Minimal markdown renderer ─────────────────────────────────────────────────
function Markdown({ text }) {
  const html = text
    // code blocks
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre class="code-block"><code class="lang-${lang}">${escHtml(code.trim())}</code></pre>`)
    // inline code
    .replace(/`([^`]+)`/g, (_, c) => `<code class="inline-code">${escHtml(c)}</code>`)
    // bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // headings
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    // bullet lists
    .replace(/^[•\-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    // numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>');

  return (
    <div
      className="markdown"
      dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
    />
  );
}

function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Booking intent detection (pure booking, not keyword in a sentence) ────────
const BOOKING_INTENT_RE = /^(book|schedule|set up|arrange|i want to (book|schedule)|check (your |his )?(availability|calendar)|when (are you|is (he|vaibhav)) (free|available))/i;

function isBookingIntent(text) {
  const t = text.trim().toLowerCase();
  // Short messages that are clearly booking requests
  if (BOOKING_INTENT_RE.test(t)) return true;
  // Longer messages: only if they don't also contain a question mark mid-sentence about something else
  if (t.length < 60 && /\b(book|schedule|availability|interview slot|set up a call)\b/.test(t)) return true;
  return false;
}

// ── Booking Modal ──────────────────────────────────────────────────────────────
function BookingModal({ onClose, onBooked }) {
  const [step, setStep] = useState('slots');
  const [slots, setSlots] = useState([]);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    const start = new Date().toISOString().split('T')[0];
    const end = new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0];
    setLoading(true);
    axios.post(`${BACKEND_URL}/availability`, { start_date: start, end_date: end })
      .then(r => { setSlots(r.data.slots || []); setLoading(false); })
      .catch(() => { setError('Could not fetch slots — try again.'); setLoading(false); });
  }, []);

  const confirm = async () => {
    if (!name.trim() || !email.trim()) { setError('Name and email are required.'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Enter a valid email address.'); return; }
    setLoading(true); setError('');
    try {
      const r = await axios.post(`${BACKEND_URL}/book`, { datetime: selected.start, name, email });
      setBooking(r.data.booking);
      setStep('done');
      onBooked?.(r.data.booking);
    } catch {
      setError('Booking failed — please try again.');
    }
    setLoading(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        <h2>📅 Schedule an Interview</h2>

        {step === 'slots' && (
          <>
            <p className="modal-sub">Select a time that works for you (next 2 weeks)</p>
            {loading && <p className="loading-text">Checking calendar…</p>}
            {error && <p className="error-text">{error}</p>}
            {!loading && slots.length === 0 && !error && (
              <p className="loading-text">No slots found — try a different date range.</p>
            )}
            <div className="slots-list">
              {slots.map((s, i) => (
                <button
                  key={i}
                  className={`slot-btn${selected?.start === s.start ? ' selected' : ''}`}
                  onClick={() => setSelected(s)}
                >
                  {s.formatted}
                  {s.source === 'fallback' && <span className="slot-fallback"> (est.)</span>}
                </button>
              ))}
            </div>
            <button className="primary-btn" disabled={!selected} onClick={() => setStep('confirm')}>
              Continue →
            </button>
          </>
        )}

        {step === 'confirm' && (
          <>
            <p className="modal-sub">Confirming: <strong>{selected.formatted}</strong></p>
            <input
              placeholder="Your full name"
              value={name}
              onChange={e => setName(e.target.value)}
              autoFocus
            />
            <input
              placeholder="Your email address"
              value={email}
              onChange={e => setEmail(e.target.value)}
              type="email"
            />
            {error && <p className="error-text">{error}</p>}
            <div className="modal-actions">
              <button className="secondary-btn" onClick={() => setStep('slots')}>← Back</button>
              <button className="primary-btn" disabled={loading} onClick={confirm}>
                {loading ? 'Booking…' : 'Confirm Booking'}
              </button>
            </div>
          </>
        )}

        {step === 'done' && (
          <div className="booking-confirmed">
            <div className="check-icon">✓</div>
            <p>{booking?.message || 'Interview booked! Check your email for the invite.'}</p>
            <a
              href={`https://cal.com/aryan-pandey-wpce3h/30min`}
              target="_blank"
              rel="noreferrer"
              className="cal-link"
            >
              View on Cal.com →
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "Why is Vaibhav the right person for this role?",
  "Walk me through IncidentCommander — design, tradeoffs, and what you'd change",
  "What does his resume say about his experience?",
  "Tell me about the Email Spam Classifier — how does the model work?",
  "What's his GitHub commit history look like?",
  "Schedule an interview",
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBooking, setShowBooking] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMsg = useCallback((msg) => setMessages(prev => [...prev, msg]), []);

  const sendMessage = useCallback(async (overrideInput) => {
    const text = (overrideInput ?? input).trim();
    if (!text || loading) return;

    setInput('');
    addMsg({ role: 'user', content: text });

    // Pure booking intent → open modal directly
    if (isBookingIntent(text)) {
      addMsg({ role: 'assistant', content: "Sure! Opening the booking panel — pick a slot that works for you.", action: 'book' });
      setTimeout(() => setShowBooking(true), 300);
      return;
    }

    setLoading(true);

    // Use HTTP streaming via fetch (SSE-style) — WebSocket is secondary
    // Railway supports HTTP but WS may not be available on all plans
    try {
      const r = await axios.post(`${BACKEND_URL}/chat`, { message: text, session_id: sessionId });
      addMsg({ role: 'assistant', content: r.data.response, sources: r.data.sources });
      setSessionId(r.data.session_id);
      setLoading(false);
      return;
    } catch (err) {
      console.error('HTTP chat failed:', err);
      addMsg({ role: 'assistant', content: '⚠️ Could not reach the server — please try again.' });
      setLoading(false);
      return;
    }
  }, [input, loading, sessionId, addMsg]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <div className="App">
      {showBooking && (
        <BookingModal
          onClose={() => setShowBooking(false)}
          onBooked={(booking) => {
            setShowBooking(false);
            addMsg({ role: 'assistant', content: `✅ **Booked!** ${booking?.message || 'Interview confirmed.'}` });
          }}
        />
      )}

      <div className="chat-container">
        <header className="chat-header">
          <div className="header-top">
            <div className="header-info">
              <div className="avatar">S</div>
              <div>
                <h1>Sam</h1>
                <p>AI representative for <strong>Vaibhav Pandey</strong> · AI Engineer @ Scaler</p>
              </div>
            </div>
            <div className="header-actions">
              {PHONE_NUMBER && (
                <a href={`tel:${PHONE_NUMBER}`} className="phone-badge" title="Call Sam">
                  📞 {PHONE_NUMBER}
                </a>
              )}
              <button className="book-btn" onClick={() => setShowBooking(true)}>
                📅 Book Interview
              </button>
            </div>
          </div>
        </header>

        <div className="messages" role="log" aria-live="polite">
          {messages.length === 0 && (
            <div className="welcome">
              <div className="welcome-avatar">👋</div>
              <h2>Hi, I'm Sam</h2>
              <p>
                Vaibhav Pandey's AI representative. I'm grounded in his actual resume,
                GitHub repos, and commit history — ask me anything specific.
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map(q => (
                  <button key={q} className="chip" onClick={() => sendMessage(q)}>{q}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              {msg.role === 'assistant' && <div className="msg-avatar">S</div>}
              <div className="bubble">
                <Markdown text={msg.content} />
                {msg.streaming && <span className="cursor" aria-hidden>▋</span>}
                {msg.action === 'book' && (
                  <button className="inline-book-btn" onClick={() => setShowBooking(true)}>
                    View available slots →
                  </button>
                )}
                {msg.sources?.length > 0 && <Sources sources={msg.sources} />}
              </div>
            </div>
          ))}

          {loading && !messages[messages.length - 1]?.streaming && (
            <div className="message assistant">
              <div className="msg-avatar">S</div>
              <div className="bubble"><span className="typing">●●●</span></div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about skills, projects, commits, or type 'book interview'…"
            disabled={loading}
            rows={2}
            aria-label="Message input"
          />
          <button
            className="send-btn"
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            aria-label="Send"
          >
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}

function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  const unique = [...new Map(
    sources.map(s => {
      const m = s?.metadata || {};
      const label = [m.source, m.repo || m.type, m.file].filter(Boolean).join(' · ');
      return [label, { label, url: m.url }];
    })
  ).values()];

  return (
    <div className="sources">
      <button className="sources-toggle" onClick={() => setOpen(o => !o)}>
        {open ? '▾' : '▸'} {unique.length} source{unique.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <div className="source-tags">
          {unique.map(({ label, url }) =>
            url
              ? <a key={label} href={url} target="_blank" rel="noreferrer" className="source-tag">{label}</a>
              : <span key={label} className="source-tag">{label}</span>
          )}
        </div>
      )}
    </div>
  );
}
