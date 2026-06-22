"use client";
import { useState } from "react";

const ROWS_PER_PAGE = 25;

interface ResultTableProps {
  columns: string[];
  rows: (string | number | null)[][];
  truncated?: boolean;
  totalRowCount?: number;
}

export function ResultTable({ columns, rows, truncated, totalRowCount }: ResultTableProps) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(rows.length / ROWS_PER_PAGE));
  const pageRows = rows.slice(page * ROWS_PER_PAGE, (page + 1) * ROWS_PER_PAGE);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-100">
            {columns.map((col) => (
              <th
                key={col}
                className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pageRows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-gray-50"}>
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className={`border border-gray-200 px-3 py-1.5 ${
                    typeof cell === "number" ? "text-right font-mono" : "text-left"
                  }`}
                >
                  {cell === null ? (
                    <span className="text-gray-400 italic">null</span>
                  ) : (
                    String(cell)
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {totalPages > 1 && (
        <div className="flex items-center gap-3 mt-2 text-sm text-gray-600">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >
            Previous
          </button>
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >
            Next
          </button>
        </div>
      )}
      {truncated && (
        <p className="text-xs text-amber-700 mt-1">
          Results truncated to {rows.length} of {totalRowCount} total rows.
        </p>
      )}
    </div>
  );
}
