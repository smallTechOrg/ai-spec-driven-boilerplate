"use client";
import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { uploadFile, UploadedFile } from "@/lib/api";

interface Props {
  sessionId: string;
  onUploaded: (file: UploadedFile) => void;
}

export default function FileUpload({ sessionId, onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      setError("Only CSV files are supported. Excel support coming in Phase 2.");
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const result = await uploadFile(sessionId, file);
      onUploaded(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  if (uploading) {
    return (
      <div className="flex flex-col items-center justify-center h-40 gap-3">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-gray-600">Profiling your data...</p>
      </div>
    );
  }

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragging ? "border-blue-500 bg-blue-50" : error ? "border-red-400 bg-red-50" : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
        }`}
      >
        <div className="text-3xl mb-2">{dragging ? "📂" : "☁️"}</div>
        <p className="font-medium text-gray-700">{dragging ? "Drop it!" : "Drop a CSV file here, or click to browse"}</p>
        <p className="text-xs text-gray-400 mt-1">CSV only — Excel support coming in Phase 2</p>
        <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={onChange} />
      </div>
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
    </div>
  );
}
