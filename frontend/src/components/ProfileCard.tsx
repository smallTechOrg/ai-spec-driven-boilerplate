import { FileProfile, ColumnProfile, QualityFlag } from "@/lib/api";
import ExportMenu from "@/components/ExportMenu";

function dtypeColor(dtype: string): string {
  if (dtype.includes("float") || dtype.includes("int")) return "bg-blue-100 text-blue-800";
  if (dtype.includes("datetime")) return "bg-yellow-100 text-yellow-800";
  if (dtype === "object" || dtype.includes("str")) return "bg-green-100 text-green-800";
  return "bg-gray-100 text-gray-700";
}

function NullBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full bg-orange-400 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pct.toFixed(1)}% null</span>
    </div>
  );
}

function ColumnRow({ col }: { col: ColumnProfile }) {
  return (
    <div className="py-2 border-b border-gray-100 last:border-0">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <span className="font-medium text-sm text-gray-800 truncate max-w-[120px]" title={col.name}>{col.name}</span>
          <span className={`text-xs px-1.5 py-0.5 rounded font-mono shrink-0 ${dtypeColor(col.dtype)}`}>{col.dtype}</span>
        </div>
        <NullBar pct={col.null_pct} />
      </div>
      {col.sample_values && col.sample_values.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {col.sample_values.map((v, i) => (
            <span key={i} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{v}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function FlagBadge({ flag }: { flag: QualityFlag }) {
  const isError = flag.type === "ERROR";
  return (
    <div className={`text-xs px-2 py-1 rounded flex items-start gap-1.5 ${isError ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800"}`}>
      <span>{isError ? "🔴" : "⚠️"}</span>
      <span>{flag.message}</span>
    </div>
  );
}

interface Props {
  filename: string;
  profile: FileProfile;
  sessionId?: string;  // optional — when present, export is wired
}

export default function ProfileCard({ filename, profile, sessionId }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-100">
        <p className="font-semibold text-gray-900 truncate" title={filename}>{filename}</p>
        <p className="text-xs text-gray-500 mt-0.5">
          {profile.row_count.toLocaleString()} rows · {profile.column_count} columns
        </p>
      </div>
      <div className="px-4 py-1 max-h-64 overflow-y-auto">
        {profile.columns.map((col) => <ColumnRow key={col.name} col={col} />)}
      </div>
      {profile.quality_flags.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-100 flex flex-col gap-1">
          {profile.quality_flags.map((flag, i) => <FlagBadge key={i} flag={flag} />)}
        </div>
      )}
      <div className="px-4 py-3 border-t border-gray-100">
        {sessionId ? (
          <ExportMenu sessionId={sessionId} />
        ) : (
          <button
            disabled
            className="w-full text-sm text-gray-400 border border-gray-200 rounded-lg py-1.5 cursor-not-allowed"
            title="No session available"
          >
            Export Data
          </button>
        )}
      </div>
    </div>
  );
}
