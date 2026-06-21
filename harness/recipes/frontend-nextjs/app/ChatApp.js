"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// All backend calls go through the same-origin /api proxy (see next.config.js),
// which rewrites to NEXT_PUBLIC_API_URL. This keeps the browser CORS-free.
const API = "/api";

// ── helpers ────────────────────────────────────────────────────────────────

function genId() {
  // crypto.randomUUID gives a collision-free per-tab id; fall back to Math.random
  // for non-secure / older contexts so this never throws.
  try {
    if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  } catch {}
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// Safe localStorage that never throws — the window.localStorage guard covers SSR
// and privacy-locked browsers. Kept for when you persist a thread/session id.
const ls = {
  get: (key) => {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set: (key, val) => {
    try {
      window.localStorage.setItem(key, val);
    } catch {}
  },
  remove: (key) => {
    try {
      window.localStorage.removeItem(key);
    } catch {}
  },
};

function getOrCreate(key, factory) {
  const v = ls.get(key);
  if (v) return v;
  const n = factory();
  ls.set(key, n);
  return n;
}

// ── Message ──────────────────────────────────────────────────────────────────
// A single chat bubble. User text is rendered plain; assistant text goes through
// react-markdown (GFM tables/strikethrough). react-markdown 10.x does NOT render
// raw HTML and rehype-raw is intentionally absent, so LLM output cannot inject
// <script>/<img onerror> — that escaping IS the XSS guard. Do not add rehype-raw.

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm
          ${
            isUser
              ? "bg-blue-600 text-white"
              : "bg-white border border-gray-200 text-gray-800 shadow-sm"
          }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || ""}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

// ── MessageList ────────────────────────────────────────────────────────────────
// Owns the scroll viewport. Renders the empty state (UI state 1) when there are
// no messages, otherwise the bubbles plus a sending indicator (UI state 2).

function MessageList({ messages, sending }) {
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.length === 0 && !sending && (
        // UI state 1 — empty
        <div className="h-full flex items-center justify-center text-gray-400 text-sm text-center">
          <p className="max-w-md">
            Send a message to the agent. This is a stub — replace the example tool and wire a
            real LLM.
          </p>
        </div>
      )}

      {messages.map((msg) => (
        <Message key={msg.id} msg={msg} />
      ))}

      {sending && (
        // UI state 2 — sending / loading
        <div className="flex justify-start mb-4" aria-live="polite">
          <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 text-sm text-gray-400 shadow-sm">
            <span className="inline-flex gap-1">
              <span className="animate-bounce">·</span>
              <span className="animate-bounce [animation-delay:0.15s]">·</span>
              <span className="animate-bounce [animation-delay:0.3s]">·</span>
            </span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

// ── InputBar ───────────────────────────────────────────────────────────────────
// Controlled text input + send button. Enter sends (Shift+Enter is free for a
// future multiline upgrade); both are disabled while a request is in flight.

function InputBar({ value, onChange, onSend, disabled }) {
  return (
    <div className="border-t bg-white px-4 py-3 flex gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSend();
          }
        }}
        placeholder="Type a message…"
        disabled={disabled}
        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm
          focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50"
        aria-label="message"
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium
          hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        aria-label="Send"
      >
        {disabled ? "…" : "Send"}
      </button>
    </div>
  );
}

// ── StubBanner ──────────────────────────────────────────────────────────────────
// Visible when the backend reports stub_mode. Tells the operator the agent is a
// placeholder so a "why is it echoing me" report never gets filed.

function StubBanner() {
  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-xs text-amber-800 text-center">
      Stub mode — the backend is running the example echo agent with a stub LLM. Replace the
      example tool and wire a real LLM.
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────────
// Owns messages / input / sending / error / stubMode state and the send() flow.
// send() POSTs { input } and reads { ok, data:{ result, run_id } } — swap its body
// for an SSE/streaming reader to go streaming; nothing else in the tree changes.

export default function ChatApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [lastInput, setLastInput] = useState(""); // for retry
  const [stubMode, setStubMode] = useState(false);

  // Mint a stable per-tab session id (unused by the generic contract, but kept so
  // wiring thread/session persistence is a one-liner later).
  useEffect(() => {
    getOrCreate("session_id", genId);
  }, []);

  // Fetch the backend's stub_mode flag on mount to drive the banner.
  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((body) => {
        if (!cancelled) setStubMode(Boolean(body?.stub_mode));
      })
      .catch(() => {
        // Health probe failing is non-fatal — just leave the banner off.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runRequest = useCallback(async (text) => {
    setSending(true);
    setError(null);
    try {
      // Contract served by both python recipes:
      //   POST /api/run { input } -> { ok: true, data: { result, run_id } }
      const res = await fetch(`${API}/api/run`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ input: text }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || `Request failed (${res.status})`);

      const data = json.data || {};
      setMessages((prev) => [
        ...prev,
        {
          id: genId(),
          role: "assistant",
          content: data.result ?? "",
          runId: data.run_id,
        },
      ]);
    } catch (e) {
      // UI state 4 — error. Surfaced as a retryable card, not a chat bubble.
      setError(e.message || "Something went wrong.");
    } finally {
      setSending(false);
    }
  }, []);

  const send = useCallback(() => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setLastInput(text);
    setMessages((prev) => [...prev, { id: genId(), role: "user", content: text }]);
    runRequest(text);
  }, [input, sending, runRequest]);

  const retry = useCallback(() => {
    if (!lastInput || sending) return;
    runRequest(lastInput);
  }, [lastInput, sending, runRequest]);

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {stubMode && <StubBanner />}

      {/* UI state 3 (response) is the rendered assistant bubbles inside MessageList. */}
      <MessageList messages={messages} sending={sending} />

      {error && (
        // UI state 4 — error card with retry
        <div className="mx-4 mb-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center justify-between gap-3">
          <span>Error: {error}</span>
          <button
            onClick={retry}
            disabled={sending || !lastInput}
            className="shrink-0 rounded-md border border-red-300 px-3 py-1 text-xs font-medium
              hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Retry
          </button>
        </div>
      )}

      <InputBar value={input} onChange={setInput} onSend={send} disabled={sending} />
    </div>
  );
}
