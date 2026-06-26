interface DataTableProps {
  data: Array<Record<string, unknown>>
}

export function DataTable({ data }: DataTableProps) {
  if (!data || data.length === 0) return null
  const headers = Object.keys(data[0])
  return (
    <div className="overflow-x-auto mt-3 rounded border border-gray-200">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="bg-gray-100">
            {headers.map((h) => (
              <th key={h} className="px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              {headers.map((h) => (
                <td key={h} className="px-3 py-2 text-gray-800 whitespace-nowrap">
                  {String(row[h] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
