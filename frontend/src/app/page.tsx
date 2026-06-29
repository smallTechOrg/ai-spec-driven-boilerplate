"use client";
import { useState, useEffect, useRef } from "react";
import FileUpload from "@/components/FileUpload";
import ProfileCard from "@/components/ProfileCard";
import ChatMessage, { LoadingMessage } from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import { createSession, sendMessage, Message, UploadedFile } from "@/lib/api";

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Create session on mount
  useEffect(() => {
    createSession()
      .then(setSessionId)
      .catch(() => setInitError("Could not connect to the server. Is it running on port 8001?"));
  }, []);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleUploaded = (file: UploadedFile) => {
    setUploadedFile(file);
    setMessages([]);
  };

  const handleSend = async (content: string) => {
    if (!sessionId || !uploadedFile) return;

    const userMsg: Message = {
      message_id: `tmp-${Date.now()}`,
      role: "user",
      content,
      chart_json: null,
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await sendMessage(sessionId, content);
      setMessages((prev) => [...prev, response]);
    } catch (e: unknown) {
      const errorMsg: Message = {
        message_id: `err-${Date.now()}`,
        role: "assistant",
        content: e instanceof Error ? e.message : "An error occurred. Please try again.",
        chart_json: null,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  if (initError) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center text-red-600 max-w-md">
          <p className="text-lg font-semibold mb-2">Connection Error</p>
          <p className="text-sm">{initError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Left panel — file upload + profile */}
      <div className="w-[30%] min-w-[260px] border-r border-gray-200 bg-white flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100">
          <h1 className="font-semibold text-gray-900 text-sm">CSV Analysis Agent</h1>
        </div>
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          {!uploadedFile && sessionId ? (
            <FileUpload sessionId={sessionId} onUploaded={handleUploaded} />
          ) : uploadedFile ? (
            <>
              <ProfileCard filename={uploadedFile.filename} profile={uploadedFile.profile} />
              <button
                disabled
                className="w-full text-xs text-gray-400 border border-gray-200 rounded-lg py-2 cursor-not-allowed"
              >
                Upload another file [Coming in Phase 2]
              </button>
            </>
          ) : null}
        </div>
      </div>

      {/* Right panel — chat */}
      <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
        {/* Message list */}
        <div className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-400 gap-2">
              <p className="text-4xl">📊</p>
              <p className="font-medium">
                {uploadedFile ? "Ask a question about your data" : "Upload a CSV file to get started"}
              </p>
              <p className="text-xs text-gray-300">Compare files across sessions — Phase 2</p>
            </div>
          )}
          {messages.map((msg) => (
            <ChatMessage key={msg.message_id} message={msg} />
          ))}
          {loading && <LoadingMessage />}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={loading} hasFile={!!uploadedFile} />
      </div>
    </div>
  );
}
