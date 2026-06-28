'use client'

import { useEffect, useState } from 'react'
import { UploadedFile, listFiles } from '@/lib/api'
import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'

export default function Home() {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)

  // Load existing files on mount
  useEffect(() => {
    listFiles()
      .then((loaded) => {
        setFiles(loaded)
        if (loaded.length > 0 && !selectedFileId) {
          setSelectedFileId(loaded[0].file_id)
        }
      })
      .catch(() => {
        // Not connected to backend yet — start empty
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleUploadSuccess(file: UploadedFile) {
    setFiles((prev) => {
      // Avoid duplicates (e.g. re-upload same file)
      const existing = prev.findIndex((f) => f.file_id === file.file_id)
      if (existing >= 0) {
        const updated = [...prev]
        updated[existing] = file
        return updated
      }
      return [file, ...prev]
    })
    setSelectedFileId(file.file_id)
  }

  const selectedFile = files.find((f) => f.file_id === selectedFileId) ?? null

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar
        files={files}
        selectedFileId={selectedFileId}
        onFileSelect={setSelectedFileId}
        onUploadSuccess={handleUploadSuccess}
      />
      <main className="flex-1 min-w-0">
        <ChatPanel
          selectedFileId={selectedFileId}
          fileName={selectedFile?.original_name ?? null}
        />
      </main>
    </div>
  )
}
