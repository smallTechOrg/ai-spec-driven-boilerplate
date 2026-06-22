"use client";
import { useRef } from "react";
import type { DatasetMeta } from "@/app/lib/types";

interface DatasetSidebarProps {
  datasets: DatasetMeta[];
  isUploading: boolean;
  uploadError: string | null;
  onUpload: (file: File) => void;
}

export function DatasetSidebar({
  datasets,
  isUploading,
  uploadError,
  onUpload,
}: DatasetSidebarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <aside className="w-64 shrink-0 border-r border-gray-200 bg-white flex flex-col p-3 gap-3">
      <h2 className="font-semibold text-gray-800 text-sm">Datasets</h2>
      <button
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="w-full py-2 px-3 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 disabled:opacity-40 transition-colors"
      >
        {isUploading ? "Uploading…" : "Upload Dataset"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.json"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) {
            onUpload(f);
            e.target.value = "";
          }
        }}
      />
      {uploadError && <p className="text-xs text-red-600">{uploadError}</p>}
      {datasets.length === 0 && !isUploading && (
        <p className="text-xs text-gray-400">
          No datasets yet. Upload a CSV or JSON file to get started.
        </p>
      )}
      <ul className="flex flex-col gap-2 overflow-y-auto">
        {datasets.map((ds) => (
          <li
            key={ds.dataset_id}
            className="p-2 rounded-lg bg-gray-50 border border-gray-200 text-xs group relative"
            title={ds.columns.map((c) => `${c.name} (${c.type})`).join(", ")}
          >
            <div className="font-medium text-gray-800 truncate">{ds.name}</div>
            <div className="text-gray-500">
              {ds.row_count.toLocaleString()} rows · {ds.columns.length} cols
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
