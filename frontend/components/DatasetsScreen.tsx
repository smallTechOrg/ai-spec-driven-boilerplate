"use client";

import { useState, useRef, useEffect } from "react";
import { API_URL } from "@/lib/api";
import { useAppContext } from "@/components/AppContext";

interface DatasetCard {
  id: string;
  name: string;
  row_count: number;
  file_format: string;
  column_schema?: Array<{ name: string; dtype: string }>;
}

export default function DatasetsScreen() {
  const { activeSessionId, setDatasetIds } = useAppContext();
  const [datasets, setDatasets] = useState<DatasetCard[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // [C-SSR-BROWSER-API]: fetch in useEffect only
  useEffect(() => {
    if (!activeSessionId) return;
    fetchDatasets(activeSessionId);
  }, [activeSessionId]);

  async function fetchDatasets(sessionId: string) {
    try {
      const resp = await fetch(`${API_URL}/datasets?session_id=${sessionId}`);
      if (resp.ok) {
        const data = await resp.json();
        const list: DatasetCard[] = Array.isArray(data) ? data : data.datasets ?? [];
        setDatasets(list);
        setDatasetIds(list.map((d) => d.id));
      }
    } catch {
      // silently ignore — backend may not be ready
    }
  }

  async function uploadFile(file: File) {
    const sessionId = activeSessionId;
    if (!sessionId) {
      setUploadError("No active session — please wait for session to load");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", sessionId);

    try {
      const xhr = new XMLHttpRequest();
      await new Promise<void>((resolve, reject) => {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            setUploadProgress(Math.round((e.loaded / e.total) * 100));
          }
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            let msg = `HTTP ${xhr.status}`;
            try {
              const body = JSON.parse(xhr.responseText);
              msg = body?.detail ?? body?.error?.message ?? msg;
            } catch {}
            reject(new Error(msg));
          }
        };
        xhr.onerror = () => reject(new Error("Network error"));
        xhr.open("POST", `${API_URL}/datasets`);
        xhr.send(formData);
      });

      await fetchDatasets(sessionId);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold text-gray-800">Datasets</h1>

      {/* Upload dropzone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragOver
            ? "border-blue-400 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:bg-gray-100"
        }`}
      >
        <p className="text-gray-600 mb-3">
          Drop a CSV, JSON, Excel, or Parquet file here, or click to browse
        </p>
        {uploading && (
          <progress
            value={uploadProgress}
            max={100}
            className="w-full mb-3 h-2"
          />
        )}
        {uploadError && (
          <p className="text-red-600 text-sm mb-3">Upload failed — {uploadError}</p>
        )}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {uploading ? "Uploading…" : "Browse files"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json,.xlsx,.parquet"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* Dataset cards */}
      {datasets.length === 0 ? (
        <div className="text-center text-gray-400 py-12 text-sm">
          No datasets yet — upload a file above to get started.
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {datasets.map((ds) => (
            <li key={ds.id} className="border rounded-lg p-4 bg-white shadow-sm">
              <h3 className="font-semibold text-gray-800 truncate">{ds.name}</h3>
              <div className="flex gap-2 mt-2">
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                  {ds.row_count} rows
                </span>
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full uppercase">
                  {ds.file_format}
                </span>
              </div>
              {ds.column_schema && ds.column_schema.length > 0 && (
                <details className="mt-3 text-sm">
                  <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
                    Schema ({ds.column_schema.length} columns)
                  </summary>
                  <ul className="mt-2 space-y-1">
                    {ds.column_schema.map((col) => (
                      <li key={col.name} className="text-xs text-gray-600 font-mono">
                        {col.name} ({col.dtype})
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
