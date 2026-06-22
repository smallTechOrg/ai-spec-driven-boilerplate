"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_URL } from "@/lib/api";
import { useAppContext } from "@/components/AppContext";

// [C-PLOTLY-SSR]: load client-only, never during SSR
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface QueryResult {
  table_markdown: string;
  chart_spec: Record<string, unknown> | null;
  row_count: number;
  sql: string;
  suggestions: string[];
}

type QueryState = "empty" | "loading" | "populated" | "error";

const EXAMPLE_CHIPS = [
  "Top 5 by revenue",
  "Count by category",
  "Show monthly trend",
];

const STUB_SUGGESTIONS = [
  "Break down by category",
  "Show trend over time",
];

export default function QueryScreen() {
  const { activeSessionId, datasetIds } = useAppContext();
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<QueryState>("empty");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function submit(q: string) {
    if (!q.trim()) return;
    setQuestion(q);
    setState("loading");

    // [C-SESSION-SCOPE]: activeSessionId from context (set in useEffect in SessionSidebar)
    // Fall back to stub value only if context hasn't loaded yet
    const sessionId = activeSessionId ?? "phase1-stub-session";

    try {
      const resp = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          dataset_ids: datasetIds,
          question: q,
        }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(body?.detail ?? `HTTP ${resp.status}`);
      }
      const data: QueryResult = await resp.json();
      setResult(data);
      setState("populated");
      setErrorMsg(null);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setState("error");
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    submit(question);
  }

  function handleChipClick(chip: string) {
    submit(chip);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(question);
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Empty state */}
      {state === "empty" && (
        <div className="flex flex-col items-center justify-center py-24 gap-6 text-center">
          <h1 className="text-2xl font-semibold text-gray-700">
            Ask a question about your data
          </h1>
          <div className="flex flex-wrap gap-2 justify-center">
            {EXAMPLE_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => handleChipClick(chip)}
                className="px-4 py-2 rounded-full bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 text-sm"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Question input — always visible when not empty */}
      {state !== "empty" && (
        <form onSubmit={handleSubmit} className="mb-6 flex gap-3 items-start">
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data..."
            disabled={state === "loading"}
            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-gray-50"
          />
          <button
            type="submit"
            disabled={state === "loading"}
            className="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm font-medium h-fit"
          >
            {state === "loading" ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Running…
              </span>
            ) : (
              "Submit"
            )}
          </button>
        </form>
      )}

      {/* Loading skeleton */}
      {state === "loading" && (
        <div className="animate-pulse space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 bg-gray-200 rounded w-full" />
          ))}
          <div className="h-48 bg-gray-200 rounded w-full mt-4" />
        </div>
      )}

      {/* Error state */}
      {state === "error" && (
        <div className="mb-4 p-4 bg-red-50 border border-red-300 rounded text-red-700 flex items-center justify-between">
          <span className="text-sm">Could not run that query — {errorMsg}</span>
          <button
            onClick={() => submit(question)}
            className="ml-4 text-sm underline hover:text-red-900"
          >
            Try again
          </button>
        </div>
      )}

      {/* Populated result — stays visible even in error state (prior result) */}
      {result && state !== "loading" && (
        <div className="space-y-6">
          {/* Row count + table */}
          <div>
            <div className="text-sm font-semibold text-gray-600 mb-2">
              {result.row_count} rows
            </div>
            <div className="overflow-x-auto border rounded">
              {/* [C-MD-RENDER]: use react-markdown + remark-gfm for GFM tables */}
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ children }) => (
                    <table className="min-w-full text-sm border-collapse">{children}</table>
                  ),
                  th: ({ children }) => (
                    <th className="px-3 py-2 bg-gray-100 border border-gray-200 text-left font-semibold">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-3 py-2 border border-gray-200">
                      {children === null || children === undefined || children === "" ? "—" : children}
                    </td>
                  ),
                }}
              >
                {result.table_markdown}
              </ReactMarkdown>
            </div>
          </div>

          {/* Chart */}
          {result.chart_spec ? (
            <div className="border rounded p-2">
              <Plot
                data={(result.chart_spec as { data: Plotly.Data[] }).data ?? []}
                layout={(result.chart_spec as { layout: Partial<Plotly.Layout> }).layout ?? {}}
                config={{ displaylogo: false, modeBarButtonsToAdd: ["downloadImage"] as any }}
                style={{ width: "100%", height: "360px" }}
              />
            </div>
          ) : (
            <div className="border rounded p-8 text-center text-gray-400 text-sm">
              No data to chart
            </div>
          )}

          {/* SQL disclosure */}
          {result.sql && (
            <details className="border rounded p-3 text-sm">
              <summary className="cursor-pointer font-medium text-gray-600">View SQL</summary>
              <pre className="mt-2 text-xs bg-gray-50 p-3 overflow-x-auto rounded whitespace-pre-wrap">
                {result.sql}
              </pre>
            </details>
          )}

          {/* Suggestion chips from API response */}
          {result.suggestions && result.suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {result.suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => handleChipClick(s)}
                  className="px-3 py-1 rounded-full bg-purple-50 border border-purple-200 text-purple-700 hover:bg-purple-100 text-sm"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Fallback stub suggestions if none from API */}
          {(!result.suggestions || result.suggestions.length === 0) && (
            <div className="flex flex-wrap gap-2">
              {STUB_SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleChipClick(s)}
                  className="px-3 py-1 rounded-full bg-gray-50 border border-gray-200 text-gray-600 hover:bg-gray-100 text-sm"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Initial question input when empty */}
      {state === "empty" && (
        <form onSubmit={handleSubmit} className="mt-4 flex gap-3 items-start">
          <textarea
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data..."
            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            type="submit"
            className="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700 text-sm font-medium h-fit"
          >
            Submit
          </button>
        </form>
      )}
    </div>
  );
}
