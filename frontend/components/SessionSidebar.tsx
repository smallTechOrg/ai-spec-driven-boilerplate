"use client";

import { useState, useEffect } from "react";
import { API_URL } from "@/lib/api";
import { useAppContext } from "@/components/AppContext";

interface Session {
  id: string;
  created_at?: string;
  title?: string;
}

export default function SessionSidebar() {
  const { activeSessionId, setActiveSessionId } = useAppContext();
  const [sessions, setSessions] = useState<Session[]>([]);

  // [C-SSR-BROWSER-API]: all API calls in useEffect only
  // [C-SESSION-SCOPE]: session ID created in useEffect, not in useState initialiser
  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        // Try to get existing sessions first
        const listResp = await fetch(`${API_URL}/sessions`);
        if (!listResp.ok) throw new Error("list failed");
        const data = await listResp.json();
        const existing: Session[] = Array.isArray(data) ? data : data.sessions ?? [];

        if (cancelled) return;

        if (existing.length > 0) {
          setSessions(existing);
          setActiveSessionId(existing[0].id);
        } else {
          // Create initial session
          const createResp = await fetch(`${API_URL}/sessions`, { method: "POST" });
          if (!createResp.ok) throw new Error("create failed");
          const newSession: Session = await createResp.json();
          if (cancelled) return;
          setSessions([newSession]);
          setActiveSessionId(newSession.id);
        }
      } catch {
        // Backend not ready — silently ignore; UI still renders with no sessions
      }
    }

    init();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleNew() {
    try {
      const resp = await fetch(`${API_URL}/sessions`, { method: "POST" });
      if (!resp.ok) return;
      const newSession: Session = await resp.json();
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
    } catch {
      // silently ignore
    }
  }

  function sessionLabel(s: Session, idx: number) {
    if (s.title) return s.title;
    return `Session ${idx + 1}`;
  }

  return (
    <aside className="w-64 bg-gray-100 border-r flex flex-col p-3 flex-shrink-0">
      <button
        onClick={handleNew}
        className="mb-3 w-full bg-blue-600 text-white py-1 rounded hover:bg-blue-700 text-sm font-medium"
      >
        + New
      </button>
      <div className="flex flex-col gap-1">
        {sessions.length === 0 ? (
          <p className="text-xs text-gray-400 px-2">No sessions yet</p>
        ) : (
          sessions.map((s, idx) => (
            <button
              key={s.id}
              onClick={() => setActiveSessionId(s.id)}
              className={`text-left px-3 py-2 rounded text-sm hover:bg-blue-200 ${
                activeSessionId === s.id ? "bg-blue-100" : ""
              }`}
            >
              {sessionLabel(s, idx)}
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
