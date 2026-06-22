"use client";

interface SqlCollapsibleProps {
  sql: string;
}

export function SqlCollapsible({ sql }: SqlCollapsibleProps) {
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
        View SQL
      </summary>
      <pre className="mt-1 p-2 bg-gray-800 text-gray-100 rounded text-xs overflow-x-auto whitespace-pre-wrap">
        {sql}
      </pre>
    </details>
  );
}
