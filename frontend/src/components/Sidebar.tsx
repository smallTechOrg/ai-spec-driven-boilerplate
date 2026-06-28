'use client'

import { UploadedFile } from '@/lib/api'
import { UploadZone } from './UploadZone'
import { SchemaPreview } from './SchemaPreview'

interface SidebarProps {
  files: UploadedFile[]
  selectedFileId: string | null
  onFileSelect: (fileId: string) => void
  onUploadSuccess: (file: UploadedFile) => void
}

export function Sidebar({ files, selectedFileId, onFileSelect, onUploadSuccess }: SidebarProps) {
  return (
    <aside className="bg-gray-50 border-r border-gray-200 h-screen overflow-y-auto flex flex-col"
      style={{ width: '280px', flexShrink: 0 }}>

      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-200">
        <h1 className="text-base font-semibold text-gray-900">Data Analysis Agent</h1>
        <p className="text-xs text-gray-500 mt-0.5">Ask questions about your CSV data</p>
      </div>

      {/* Upload zone */}
      <div className="px-4 py-4 border-b border-gray-200">
        <UploadZone onSuccess={onUploadSuccess} />
      </div>

      {/* Files list */}
      <div className="flex-1 px-4 py-3">
        {files.length > 0 && (
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Uploaded files
          </p>
        )}
        <ul className="space-y-1">
          {files.map((file) => (
            <li key={file.file_id}>
              <button
                onClick={() => onFileSelect(file.file_id)}
                className={`w-full text-left rounded-md px-3 py-2 text-sm transition-colors
                  ${selectedFileId === file.file_id
                    ? 'bg-blue-50 text-blue-700 font-medium border border-blue-200'
                    : 'text-gray-700 hover:bg-gray-100'
                  }`}
              >
                <span className="block truncate">{file.original_name}</span>
                {file.file_size_bytes != null && (
                  <span className="text-xs text-gray-400">
                    {(file.file_size_bytes / 1024).toFixed(1)} KB
                  </span>
                )}
              </button>
              {selectedFileId === file.file_id && (
                <div className="px-3">
                  <SchemaPreview file={file} />
                </div>
              )}
            </li>
          ))}
        </ul>

        {files.length === 0 && (
          <p className="text-xs text-gray-400 text-center mt-4">
            No files uploaded yet
          </p>
        )}
      </div>

      {/* PostgreSQL coming soon stub */}
      <div className="px-4 py-4 border-t border-gray-200 mt-auto">
        <div className="rounded-lg border border-gray-200 bg-white p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-600">Connect PostgreSQL</span>
            <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full border border-gray-200">
              Phase 2
            </span>
          </div>
          <p className="text-xs text-gray-400">Coming soon — connect a Postgres database to analyze SQL data.</p>
          <button
            disabled
            className="mt-2 w-full rounded-md bg-gray-100 px-3 py-1.5 text-xs text-gray-400 cursor-not-allowed border border-gray-200"
          >
            Connect database
          </button>
        </div>
      </div>
    </aside>
  )
}
