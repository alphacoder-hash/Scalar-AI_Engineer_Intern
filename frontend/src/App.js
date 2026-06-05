import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const PHONE_NUMBER = process.env.REACT_APP_PHONE_NUMBER || '';

function BookingModal({ onClose }) {
  const [step, setStep] = useState('slots'); // slots | confirm | done
  const [slots, setSlots] = useState([]);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    const start = new Date().toISOString().split('T')[0];
    const end = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
    setLoading(true);
    axios.post(`${BACKEND_URL}/availability`, { start_date: start, end_date: end })
      .then(r => { setSlots(r.data.slots || []); setLoading(false); })
      .catch(() => { setError('Could not fetch slots.'); setLoading(false); });
  }, []);

  const confirmBooking = async () => {
    if (!name.trim() || !email.trim()) { setError('Name and email required.'); return; }
    setLoading(true); setError('');
    try {
      const r = await axios.post(`${BACKEND_URL}/book`, {
        datetime: selected.start, name, email
      });
      setBooking(r.data.booking);
      setStep('done');
    } catch {
      setError('Booking failed. Try again.');
    }
    setLoading(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2>Schedule an Interview</h2>

        {step === 'slots' && (
          <>
            <p className="modal-sub">Pick a time that works for you</p>
            {loading && <p className="loading-text">Loading slots...</p>}
            {error && <p className="error-text">{error}</p>}
            <div className="slots-list">
              {slots.map((s, i) => (
                <button
                  key={i}
                  className={`slot-btn ${selected?.start === s.start ? 'selected' : ''}`}
                  onClick={() => setSelected(s)}
                >
                  {s.formatted}
                </button>
              ))}
            </div>
            <button
              className="primary-btn"
              disabled={!selected}
              onClick={() => setStep('confirm')}
            >
              Continue →
            </button>
          </>
        )}

        {step === 'confirm' && (
          <>
            <p className="modal-sub">Selected: <strong>{selected.formatted}</strong></p>
            <input placeholder="Your full name" value={name} onChange={e => setName(e.target.value)} />
            <input placeholder="Your email" value={email} onChange={e => setEmail(e.target.value)} />
            {error && <p className="error-text">{error}</p>}
            <button className="primary-btn" disabled={loading} onClick={confirmBooking}>
              {loading ? 'Booking...' : 'Confirm Booking'}
            </button>
          </>
        )}

        {step === 'done' && (
          <div className="booking-confirmed">
            <div className="check-icon">✓</div>
            <p>{booking?.message || 'Interview booked!'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBooking, setShowBooking] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Detect booking intent
    if (/schedule|book|interview|available|availability/i.test(input)) {
      setMessages(prev => [...prev, { role: 'user', content: input }]);
      setInput('');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Sure! Let me pull up available slots for you.",
        action: 'book'
      }]);
      setTimeout(() => setShowBooking(true), 600);
      return;
    }

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // Use streaming endpoint — handle both http:// and https://
    const wsUrl = BACKEND_URL.replace(/^https/, 'wss').replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsUrl}/chat/stream`);
    let buffer = '';
    let sid = sessionId;

    ws.onopen = () => ws.send(JSON.stringify({ message: input, session_id: sid }));

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'content') {
        buffer += data.content;
        sid = data.session_id;
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === 'assistant' && last?.streaming) {
            return [...prev.slice(0, -1), { ...last, content: buffer }];
          }
          return [...prev, { role: 'assistant', content: buffer, streaming: true }];
        });
      } else if (data.type === 'sources') {
        setSessionId(data.session_id);
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.streaming) return [...prev.slice(0, -1), { ...last, streaming: false, sources: data.sources }];
          return prev;
        });
        setLoading(false);
        ws.close();
      } else if (data.type === 'error') {
        setLoading(false);
        ws.close();
      }
    };

    ws.onerror = async () => {
      // Fallback to HTTP
      try {
        const r = await axios.post(`${BACKEND_URL}/chat`, { message: input, session_id: sessionId });
        setMessages(prev => [...prev, { role: 'assistant', content: r.data.response, sources: r.data.sources }]);
        setSessionId(r.data.session_id);
      } catch {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Something went wrong. Please try again.' }]);
      }
      setLoading(false);
    };
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <div className="App">
      {showBooking && <BookingModal onClose={() => setShowBooking(false)} />}

      <div className="chat-container">
        <div className="chat-header">
          <div className="header-top">
            <div>
              <h1>Chat with Sam</h1>
              <p>AI representative for Vaibhav Pandey · AI Engineer @ Scaler</p>
            </div>
            <div className="header-actions">
              {PHONE_NUMBER && (
                <a href={`tel:${PHONE_NUMBER}`} className="phone-badge">
                  📞 {PHONE_NUMBER}
                </a>
              )}
              <button className="book-btn" onClick={() => setShowBooking(true)}>
                📅 Book Interview
              </button>
            </div>
          </div>
        </div>

        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <h2>👋 Hi! I'm Sam</h2>
              <p>Vaibhav's AI representative. Ask me anything about his background, projects, or schedule a call.</p>
              <div className="suggestion-chips">
                {["Why is Vaibhav right for this role?", "Tell me about IncidentCommander", "What's his tech stack?", "Schedule an interview"].map(q => (
                  <button key={q} className="chip" onClick={() => { setInput(q); }}>{q}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-content">
                {msg.content}
                {msg.streaming && <span className="cursor">▋</span>}
              </div>
              {msg.action === 'book' && (
                <button className="inline-book-btn" onClick={() => setShowBooking(true)}>
                  View available slots →
                </button>
              )}
              {msg.sources?.length > 0 && (
                <details className="sources">
                  <summary>Sources ({msg.sources.length})</summary>
                  {msg.sources.map((s, i) => (
                    <span key={i} className="source-tag">{s.metadata?.source} · {s.metadata?.repo || s.metadata?.type}</span>
                  ))}
                </details>
              )}
            </div>
          ))}

          {loading && !messages[messages.length - 1]?.streaming && (
            <div className="message assistant">
              <div className="message-content typing">●●●</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about skills, projects, or type 'book interview'..."
            disabled={loading}
            rows={2}
          />
          <button onClick={sendMessage} disabled={loading || !input.trim()}>Send</button>
        </div>
      </div>
    </div>
  );
}

export default App;
