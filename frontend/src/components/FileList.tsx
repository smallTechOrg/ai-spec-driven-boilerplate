"use client";
import { useState } from "react";
import ProfileCard from "@/components/ProfileCard";
import FileUpload from "@/components/FileUpload";
import { UploadedFile } from "@/lib/api";

interface Props {
  files: UploadedFile[];
  sessionId: string;
  onFileAdded: (file: UploadedFile) => void;
}

export default function FileList({ files, sessionId, onFileAdded }: Props) {
  const [showUpload, setShowUpload] = useState(false);

  const handleUploaded = (file: UploadedFile) => {
    onFileAdded(file);
    setShowUpload(false);
  };

  return (
    <div className="flex flex-col gap-3">
      {files.map((f) => (
        <ProfileCard key={f.file_id} filename={f.filename} profile={f.profile} sessionId={sessionId} />
      ))}

      {showUpload ? (
        <FileUpload sessionId={sessionId} onUploaded={handleUploaded} />
      ) : (
        <button
          onClick={() => setShowUpload(true)}
          className="w-full text-xs text-blue-600 border border-blue-200 rounded-lg py-2 hover:bg-blue-50 transition-colors"
        >
          + Add another file
        </button>
      )}
    </div>
  );
}
