"use client";
import { useState, KeyboardEvent } from "react";

interface Props {
  onSend: (content: string) => void;
  disabled: boolean;
  hasFile: boolean;
}

export default function ChatInput({ onSend, disabled, hasFile }: Props) {
  const [value, setValue] = useState("");

  const send = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {!hasFile && (
        <p className="text-xs text-amber-600 mb-2">Upload a CSV file first to start asking questions.</p>
      )}
      {disabled && hasFile && (
        <p className="text-xs text-blue-600 mb-2">Analyzing your data...</p>
      )}
      <div className="flex gap-2 items-end">
        <textarea
          className="flex-1 resize-none border border-gray-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          placeholder={hasFile ? "Ask a question about your data..." : "Upload a CSV file first"}
          rows={2}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled || !hasFile}
        />
        <button
          onClick={send}
          disabled={disabled || !hasFile || !value.trim()}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  );
}
