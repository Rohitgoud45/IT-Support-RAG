import { useRef, useEffect, useState } from "react";

const EXAMPLES = [
  "VPN says error 809. What do I do?",
  "How long is my account locked after failed logins?",
  "I clicked a link in a phishing email",
  "Outlook says Disconnected but webmail works",
  "Which printer do I use on the third floor?",
  "How do I bake chocolate chip cookies?",
];

function refusalReason(msg) {
  if (msg.refused_by === "distance") {
    const d = msg.best_distance != null ? msg.best_distance.toFixed(2) : "?";
    return `Refused before calling the AI: the closest doc was too far away (distance ${d} > ${msg.max_distance}). No tokens spent.`;
  }
  if (msg.refused_by === "model") return "The AI read the closest docs and said they don't answer this, so it didn't guess.";
  if (msg.refused_by === "unparseable") return "The AI's reply wasn't valid, so the assistant refused instead of showing it.";
  return null;
}

async function fetchHealth() {
  try {
    const res = await fetch("/api/health");
    if (res.ok) return await res.json();
  } catch {
    // fallback
  }
  return null;
}

async function ask(question) {
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "The assistant is unavailable. Try again in a moment.");
  }
  return res.json();
}

function Answer({ msg }) {
  const [copied, setCopied] = useState(false);

  if (msg.error) {
    return (
      <div className="answer error-box" role="alert">
        <div className="answer-header">
          <span className="badge badge-error">Error</span>
        </div>
        <p className="error-text">{msg.error}</p>
      </div>
    );
  }

  function handleCopy() {
    // Clipboard is blocked on plain-http non-localhost pages; only claim success when it worked.
    navigator.clipboard
      ?.writeText(msg.answer)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {});
  }

  return (
    <div className={msg.answerable ? "answer" : "answer none"}>
      <div className="answer-header">
        <span className={msg.answerable ? "badge badge-success" : "badge badge-warning"}>
          {msg.answerable ? "Grounded Answer" : "Out of Scope / Help Desk"}
        </span>
        <button
          className="copy-btn"
          onClick={handleCopy}
          title="Copy answer"
          aria-label="Copy answer to clipboard"
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>

      <div className="answer-text">{msg.answer}</div>

      {!msg.answerable && refusalReason(msg) && <p className="why">{refusalReason(msg)}</p>}

      {msg.sources?.length > 0 && (
        <div className="sources-container">
          <p className="sources-title">Verified Sources ({msg.sources.length})</p>
          <div className="sources">
            {msg.sources.map((s) => (
              <details key={s.id}>
                <summary>
                  <span className="src-id">[{s.id}]</span>
                  <span className="src-name">{s.title}</span>
                  <span className="src-file">{s.source}</span>
                </summary>
                <div className="snippet-container">
                  <p className="snippet">{s.snippet}</p>
                </div>
              </details>
            ))}
          </div>
        </div>
      )}

      {msg.latency_ms != null && (
        <p className="meta">
          {(msg.latency_ms / 1000).toFixed(1)}s
          {msg.best_distance != null && ` · closest doc distance ${msg.best_distance.toFixed(2)}`}
        </p>
      )}
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    fetchHealth().then(setHealth);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function submit(text) {
    const question = text.trim();
    if (question.length < 3 || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text: question }]);
    try {
      const data = await ask(question);
      setMessages((m) => [...m, { role: "assistant", ...data }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", error: e.message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header>
        <div className="header-top">
          <div>
            <h1>IT Support Assistant</h1>
            <p className="subtitle">
              Reliable answers grounded in our verified IT knowledge base with strict refusal guards.
            </p>
          </div>
          {messages.length > 0 && (
            <button className="clear-btn" onClick={() => setMessages([])}>
              Clear Chat
            </button>
          )}
        </div>

        {health && (
          <div className="system-status">
            <span className="status-pill status-online">
              <span className="dot"></span> Online
            </span>
            <span className="status-pill">
              Knowledge: {health.chunks} chunks
            </span>
            <span className="status-pill">
              Provider: {health.provider} {health.model ? `(${health.model})` : ""}
            </span>
          </div>
        )}
      </header>

      <main aria-live="polite">
        {messages.length === 0 && (
          <div className="empty">
            <div className="empty-card">
              <h2>How can I help you today?</h2>
              <p>
                Ask about VPN, passwords, MFA, Wi-Fi, printers, email, Teams, software installs, file access, phishing, or laptops.
                Try something off-topic too and watch it refuse instead of guessing.
              </p>
              <div className="chips">
                {EXAMPLES.map((q) => (
                  <button key={q} onClick={() => submit(q)} className="chip-btn">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="user-message-container">
              <p className="user">{m.text}</p>
            </div>
          ) : (
            <Answer key={i} msg={m} />
          )
        )}

        {busy && (
          <div className="busy-card">
            <div className="spinner"></div>
            <span>Consulting knowledge base & verifying retrieval guards…</span>
          </div>
        )}
        <div ref={endRef} />
      </main>

      <form onSubmit={(e) => { e.preventDefault(); submit(input); }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe your IT issue (e.g., 'How do I reconnect to Corp-Secure Wi-Fi?')"
          aria-label="Your question"
          maxLength={500}
        />
        <button type="submit" disabled={busy || input.trim().length < 3}>
          {busy ? "Thinking…" : "Ask"}
        </button>
      </form>
    </div>
  );
}
