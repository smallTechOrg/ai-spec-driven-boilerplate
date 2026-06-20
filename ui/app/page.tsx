// ui/app/page.tsx — the accessible names below are the e2e contract; do not rename without updating the journey.
"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Page() {
  const [goal, setGoal] = useState("");
  const [answer, setAnswer] = useState("");
  const [runId, setRunId] = useState("");
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setAnswer("");
    setRunId("");
    try {
      const sid = crypto.randomUUID();
      const res = await fetch("http://localhost:8001/runs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ goal, session_id: sid }),
      });
      const json = await res.json();
      setAnswer(json.data?.answer ?? json.error?.message ?? "");
      setRunId(json.data?.run_id ?? "");
    } catch (e: any) {
      setAnswer("Request failed: " + (e?.message ?? String(e)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "system-ui", padding: "0 1rem" }}>
      <h1>Support Triage Agent</h1>
      <p style={{ color: "#6b7280" }}>
        Paste a support ticket. The agent classifies its urgency and category and drafts a suggested reply.
      </p>
      <textarea
        aria-label="goal"
        placeholder="Paste the support ticket (e.g. 'I was charged twice for my subscription and want a refund.')"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        rows={6}
        style={{ width: "100%", padding: 8, boxSizing: "border-box" }}
      />
      <button onClick={run} disabled={loading || !goal.trim()} style={{ marginTop: 8, padding: "8px 16px" }}>
        {loading ? "Triaging…" : "Run"}
      </button>
      <div data-testid="answer" style={{ marginTop: 16, lineHeight: 1.5 }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
      </div>
      {runId && (
        <p style={{ marginTop: 16 }}>
          <a href="http://localhost:8001/traces">trace</a>
        </p>
      )}
    </main>
  );
}
