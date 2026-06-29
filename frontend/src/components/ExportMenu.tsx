"use client";
import { useState } from "react";
import { exportResult } from "@/lib/api";

interface Props {
  sessionId: string;
}

export default function ExportMenu({ sessionId }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    try {
      const blob = await exportResult(sessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "result.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleExport}
        disabled={loading}
        className="w-full text-sm text-blue-700 border border-blue-300 rounded-lg py-1.5 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Exporting..." : "Export CSV"}
      </button>
      {error && <p className="text-xs text-red-500 mt-1 text-center">{error}</p>}
    </div>
  );
}
