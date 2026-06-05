import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const PHONE   = process.env.REACT_APP_PHONE_NUMBER || '';

// ── tiny markdown renderer ────────────────────────────────────────────────────
function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function renderMd(raw) {
  let s = raw
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_,l,c) =>
      `<pre class="cb"><code>${esc(c.trim())}</code></pre>`)
    .replace(/`([^`\n]+)`/g, (_,c) => `<code class="ic">${esc(c)}</code>`)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/^### (.+)$/gm,   '<h4>$1</h4>')
    .replace(/^## (.+)$/gm,    '<h3>$1</h3>')
    .replace(/^[•\-*] (.+)$/gm,'<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)\n?(?!<li>)/g, m => `<ul>${m}</ul>`)
    .replace(/\n{2,}/g,'</p><p>')
    .replace(/\n/g,'<br/>');
  return `<p>${s}</p>`;
}
function MD({ text }) {
  return <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(text) }} />;
}

// ── booking intent ────────────────────────────────────────────────────────────
function isBooking(t) {
  t = t.trim().toLowerCase();
  // Explicit scheduling phrases regardless of length
  if (/\b(book|schedule|set up|arrange)\b.{0,35}\b(interview|call|meeting|slot|time)\b/.test(t)) return true;
  // Short unambiguous checks
  if (t.length < 70 && /\b(check (your |his )?(availability|calendar)|when (are you|is (he|vaibhav)) (free|available)|find a time|interview slot)\b/.test(t)) return true;
  return false;
}

// ── BookingModal ──────────────────────────────────────────────────────────────
function BookingModal({ onClose, onBooked }) {
  const [step, setStep]       = useState('slots');
  const [slots, setSlots]     = useState([]);
  const [picked, setPicked]   = useState(null);
  const [name, setName]       = useState('');
  const [email, setEmail]     = useState('');
  const [busy, setBusy]       = useState(false);
  const [err, setErr]         = useState('');
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    const s = new Date().toISOString().split('T')[0];
    const e = new Date(Date.now() + 14*86400000).toISOString().split('T')[0];
    setBusy(true);
    axios.post(`${BACKEND}/availability`, { start_date: s, end_date: e })
      .then(r => { setSlots(r.data.slots || []); setBusy(false); })
      .catch(() => { setErr('Could not load slots — try again.'); setBusy(false); });
  }, []);

  async function confirm() {
    if (!name.trim() || !email.trim()) { setErr('Name and email required.'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setErr('Enter a valid email.'); return; }
    setBusy(true); setErr('');
    try {
      const r = await axios.post(`${BACKEND}/book`, { datetime: picked.start, name, email });
      setBooking(r.data.booking); setStep('done');
      onBooked?.(r.data.booking);
    } catch { setErr('Booking failed — please try again.'); }
    setBusy(false);
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <button className="x-btn" onClick={onClose}>✕</button>
        <h2>Schedule an Interview</h2>

        {step === 'slots' && (<>
          <p className="sub">Pick a slot from the next 2 weeks</p>
          {busy && <p className="dim">Loading calendar…</p>}
          {err  && <p className="err">{err}</p>}
          {!busy && !err && slots.length === 0 && <p className="dim">No slots found.</p>}
          <div className="slot-list">
            {slots.map((s,i) => (
              <button key={i}
                className={`slot${picked?.start===s.start?' on':''}`}
                onClick={() => setPicked(s)}>
                {s.formatted}
              </button>
            ))}
          </div>
          <button className="btn-primary" disabled={!picked} onClick={() => setStep('confirm')}>
            Continue →
          </button>
        </>)}

        {step === 'confirm' && (<>
          <p className="sub">Slot: <strong>{picked.formatted}</strong></p>
          <input placeholder="Your full name"    value={name}  onChange={e=>setName(e.target.value)} autoFocus />
          <input placeholder="Your email"        value={email} onChange={e=>setEmail(e.target.value)} type="email" />
          {err && <p className="err">{err}</p>}
          <div className="row">
            <button className="btn-sec" onClick={() => setStep('slots')}>← Back</button>
            <button className="btn-primary" disabled={busy} onClick={confirm}>
              {busy ? 'Booking…' : 'Confirm'}
            </button>
          </div>
        </>)}

        {step === 'done' && (
          <div className="done">
            <div className="tick">✓</div>
            <p>{booking?.message || 'Interview booked! Check your email.'}</p>
            <a href="https://cal.com/aryan-pandey-wpce3h/30min"
               target="_blank" rel="noreferrer" className="cal-a">
              View on Cal.com →
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sources ───────────────────────────────────────────────────────────────────
function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  const uniq = [...new Map(sources.map(s => {
    const m = s?.metadata || {};
    const label = [m.source, m.repo||m.type, m.file].filter(Boolean).join(' · ');
    return [label, { label, url: m.url }];
  })).values()];

  return (
    <div className="src">
      <button className="src-btn" onClick={() => setOpen(o=>!o)}>
        {open?'▾':'▸'} {uniq.length} source{uniq.length!==1?'s':''}
      </button>
      {open && (
        <div className="src-tags">
          {uniq.map(({label,url}) => url
            ? <a key={label} href={url} target="_blank" rel="noreferrer" className="tag">{label}</a>
            : <span key={label} className="tag">{label}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
const CHIPS = [
  "Why is Vaibhav right for this AI Engineer role?",
  "Walk me through IncidentCommander — design & tradeoffs",
  "What's on his resume? Education, experience, skills",
  "How does the Email Spam Classifier model work?",
  "Book an interview",
];

export default function App() {
  const [msgs,    setMsgs]    = useState([]);
  const [input,   setInput]   = useState('');
  const [loading, setLoading] = useState(false);
  const [booking, setBooking] = useState(false);
  const sessionRef  = useRef(null);   // avoids stale-closure on sessionId
  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }); }, [msgs]);

  async function send(text) {
    text = (text ?? input).trim();
    if (!text || loading) return;
    setInput('');

    setMsgs(prev => [...prev, { role:'user', content:text }]);

    if (isBooking(text)) {
      setMsgs(prev => [...prev, { role:'assistant', content:"Sure! Let me pull up available slots for you.", action:'book' }]);
      setTimeout(() => setBooking(true), 200);
      return;
    }

    setLoading(true);
    // Add a placeholder that we'll fill chunk by chunk
    setMsgs(prev => [...prev, { role:'assistant', content:'', thinking:true }]);

    const wsUrl = BACKEND.replace(/^http/, 'ws') + '/chat/stream';
    let ws;
    try {
      ws = new WebSocket(wsUrl);
    } catch(_) {
      ws = null;
    }

    if (ws) {
      let opened = false;
      ws.onopen = () => {
        opened = true;
        ws.send(JSON.stringify({ message: text, session_id: sessionRef.current }));
      };
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'content') {
          setMsgs(prev => {
            const rest = prev.filter(m => !m.thinking);
            const last = rest[rest.length - 1];
            if (last && last.role === 'assistant' && !last.thinking) {
              return [...rest.slice(0,-1), { ...last, content: last.content + data.content }];
            }
            return [...rest, { role:'assistant', content: data.content }];
          });
        } else if (data.type === 'sources') {
          if (data.session_id) sessionRef.current = data.session_id;
          setMsgs(prev => {
            const copy = [...prev];
            const idx  = copy.map(m=>m.role).lastIndexOf('assistant');
            if (idx !== -1) copy[idx] = { ...copy[idx], sources: data.sources, thinking: false };
            return copy;
          });
          setLoading(false);
          ws.close();
        } else if (data.type === 'error') {
          setMsgs(prev => {
            const rest = prev.filter(m => !m.thinking);
            return [...rest, { role:'assistant', content: data.content || 'Something went wrong.' }];
          });
          setLoading(false);
          ws.close();
        }
      };
      ws.onerror = () => {
        if (!opened) fallbackHttp(text);
        else { setLoading(false); ws.close(); }
      };
      ws.onclose = () => { setLoading(false); };
    } else {
      fallbackHttp(text);
    }
  }

  async function fallbackHttp(text) {
    try {
      const r = await axios.post(`${BACKEND}/chat`, {
        message: text,
        session_id: sessionRef.current,
      });
      sessionRef.current = r.data.session_id;
      setMsgs(prev => {
        const rest = prev.filter(m => !m.thinking);
        return [...rest, { role:'assistant', content:r.data.response, sources:r.data.sources }];
      });
    } catch(e) {
      console.error(e);
      setMsgs(prev => {
        const rest = prev.filter(m => !m.thinking);
        return [...rest, { role:'assistant', content:'Something went wrong — please try again.' }];
      });
    }
    setLoading(false);
  }

  function onKey(e) {
    if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }

  return (
    <div className="app">
      {booking && (
        <BookingModal
          onClose={() => setBooking(false)}
          onBooked={b => {
            setBooking(false);
            setMsgs(prev => [...prev, {
              role:'assistant',
              content:`✅ **Booked!** ${b?.message||'Interview confirmed — check your email.'}`
            }]);
          }}
        />
      )}

      <div className="window">
        {/* ── header ── */}
        <header className="hdr">
          <div className="hdr-left">
            <div className="ava">S</div>
            <div>
              <div className="hdr-name">Sam <span className="online">● online</span></div>
              <div className="hdr-sub">AI rep for <strong>Vaibhav Pandey</strong> · AI Engineer @ Scaler</div>
            </div>
          </div>
          <div className="hdr-right">
            {PHONE && (
              <a href={`tel:${PHONE}`} className="pill-phone">📞 {PHONE}</a>
            )}
            <button className="pill-book" onClick={() => setBooking(true)}>📅 Book Interview</button>
          </div>
        </header>

        {/* ── messages ── */}
        <div className="feed">
          {msgs.length === 0 && (
            <div className="empty">
              <div className="empty-ava">🤖</div>
              <h2>Hi, I'm Sam</h2>
              <p>Vaibhav Pandey's AI representative. I'm grounded in his actual resume, GitHub repos, and commit history — ask me anything specific.</p>
              <div className="chips">
                {CHIPS.map(q => (
                  <button key={q} className="chip" onClick={() => send(q)}>{q}</button>
                ))}
              </div>
            </div>
          )}

          {msgs.map((m, i) => (
            <div key={i} className={`row ${m.role}`}>
              {m.role==='assistant' && <div className="bubble-ava">S</div>}
              <div className={`bubble ${m.thinking?'thinking':''}`}>
                {m.thinking
                  ? <span className="dots"><span/><span/><span/></span>
                  : <MD text={m.content} />
                }
                {m.action==='book' && (
                  <button className="inline-book" onClick={() => setBooking(true)}>
                    View available slots →
                  </button>
                )}
                {m.sources?.length > 0 && <Sources sources={m.sources} />}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* ── input ── */}
        <div className="composer">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask about skills, projects, commits… or 'book interview'"
            disabled={loading}
            rows={1}
          />
          <button className="send" onClick={() => send()} disabled={loading || !input.trim()}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
