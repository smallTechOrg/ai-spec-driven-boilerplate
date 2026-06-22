"use client";
import { useState, KeyboardEvent } from "react";

interface ChatInputProps {
  hasDatasets: boolean;
  isQuerying: boolean;
  onSubmit: (question: string) => void;
}

export function ChatInput({ hasDatasets, isQuerying, onSubmit }: ChatInputProps) {
  const [value, setValue] = useState("");
  const disabled = !hasDatasets || isQuerying;

  const handleSubmit = () => {
    if (!value.trim() || disabled) return;
    onSubmit(value.trim());
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-3 flex gap-2">
      <div
        className="relative flex-1"
        title={!hasDatasets ? "Upload a dataset first." : undefined}
      >
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={
            hasDatasets
              ? "Ask a question about your data…"
              : "Upload a dataset to start asking questions."
          }
          rows={2}
          className="w-full resize-none border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
        />
      </div>
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed self-end"
      >
        {isQuerying ? "…" : "Send"}
      </button>
    </div>
  );
}
