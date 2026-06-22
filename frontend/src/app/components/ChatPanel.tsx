"use client";
import { useEffect, useRef } from "react";
import type { QueryResult } from "@/app/lib/types";
import { ResultTable } from "./ResultTable";
import { SqlCollapsible } from "./SqlCollapsible";
import { ChatInput } from "./ChatInput";

export interface Message {
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  result?: QueryResult | null;
  error?: string | null;
  timestamp: string;
}

interface ChatPanelProps {
  messages: Message[];
  hasDatasets: boolean;
  isQuerying: boolean;
  onSubmit: (question: string) => void;
}

export function ChatPanel({ messages, hasDatasets, isQuerying, onSubmit }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm text-center mt-8">
            Upload a dataset to start asking questions.
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "user" ? (
              <div className="max-w-lg bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 text-sm">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-3xl bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 text-sm shadow-sm">
                {msg.error ? (
                  <p className="text-red-600">{msg.error}</p>
                ) : msg.result ? (
                  <>
                    <ResultTable
                      columns={msg.result.columns}
                      rows={msg.result.rows}
                      truncated={msg.result.truncated}
                      totalRowCount={msg.result.total_row_count}
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      {msg.result.truncated
                        ? `Results truncated to ${msg.result.row_count} of ${msg.result.total_row_count} total rows.`
                        : `Returned ${msg.result.row_count} row(s).`}
                    </p>
                    {msg.sql && <SqlCollapsible sql={msg.sql} />}
                  </>
                ) : (
                  <p className="text-gray-600">{msg.content}</p>
                )}
              </div>
            )}
          </div>
        ))}
        {isQuerying && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 text-sm text-gray-400 animate-pulse">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <ChatInput hasDatasets={hasDatasets} isQuerying={isQuerying} onSubmit={onSubmit} />
    </div>
  );
}
