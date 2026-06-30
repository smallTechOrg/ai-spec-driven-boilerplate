"use client";

import { useState } from "react";
import { QualityReport, QualityIssue } from "@/lib/api";

interface Props {
  report: QualityReport;
}

function totalIssueCount(report: QualityReport): number {
  return report.files.reduce((sum, f) => sum + f.issues.length, 0);
}

function IssueIcon({ type }: { type: QualityIssue["type"] }) {
  if (type === "WARNING" || type === "ERROR") {
    return (
      <svg
        className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
        />
      </svg>
    );
  }
  // INFO
  return (
    <svg
      className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20A10 10 0 0012 2z"
      />
    </svg>
  );
}

export default function DataQualityNotice({ report }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!report.has_issues) return null;

  const issueCount = totalIssueCount(report);
  const allIssues: Array<QualityIssue & { filename: string }> = report.files.flatMap((f) =>
    f.issues.map((issue) => ({ ...issue, filename: f.filename }))
  );

  return (
    <div className="mb-2 max-w-[80%]">
      <div className="rounded-2xl bg-amber-50 border-l-4 border-amber-400 shadow-sm overflow-hidden">
        {/* Header — always visible, clickable */}
        <button
          onClick={() => setExpanded((prev) => !prev)}
          className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-amber-100 transition-colors"
          aria-expanded={expanded}
        >
          {/* Warning icon */}
          <svg
            className="w-4 h-4 text-amber-500 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
            />
          </svg>

          <span className="text-xs font-semibold text-amber-700 flex-1">
            Data quality notice
          </span>

          <span className="text-xs text-amber-600 mr-1">
            {issueCount} {issueCount === 1 ? "issue" : "issues"} found
          </span>

          {/* Chevron — rotates when expanded */}
          <svg
            className={`w-4 h-4 text-amber-500 flex-shrink-0 transition-transform duration-200 ${
              expanded ? "rotate-180" : "rotate-0"
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Expandable content */}
        {expanded && (
          <div className="px-4 pb-3 border-t border-amber-200">
            {/* Auto-fixed actions */}
            {report.clean_actions.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-amber-700 mb-1.5">Automatically fixed:</p>
                <ul className="space-y-1">
                  {report.clean_actions.map((action, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                      <span className="text-green-600 font-bold flex-shrink-0">&#10003;</span>
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Detected issues */}
            {allIssues.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-amber-700 mb-1.5">Detected:</p>
                <ul className="space-y-1.5">
                  {allIssues.map((issue, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                      <IssueIcon type={issue.type} />
                      <span className="leading-relaxed">{issue.detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Footer */}
            <p className="text-xs text-amber-600 mt-3 pt-2 border-t border-amber-200">
              These issues were detected before answering. Auto-fixes have already been applied.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
