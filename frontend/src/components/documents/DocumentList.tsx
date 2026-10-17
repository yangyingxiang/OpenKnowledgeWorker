'use client';

import { useRef, useState } from 'react';
import { FileText, Trash2, Upload } from 'lucide-react';
import type { Document } from '@/lib/api';
import { formatFileSize, mimeIcon } from '@/lib/documents/parseText';

/** Left column of the Documents page: drag-and-drop upload zone plus the uploaded documents. */
export function DocumentList({
  docs,
  selectedDocId,
  uploading,
  onUpload,
  onPreview,
  onDelete,
}: {
  docs: Document[];
  selectedDocId: string | undefined;
  uploading: boolean;
  onUpload: (files: FileList | null) => void;
  onPreview: (doc: Document) => void;
  onDelete: (docId: string) => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    onUpload(e.dataTransfer.files);
  };

  return (
    <div className="w-[420px] border-r border-[var(--okw-border)] bg-white flex flex-col shrink-0">
      {/* Upload zone */}
      <div
        className={`m-4 p-6 border-2 border-dashed rounded-xl text-center transition-colors cursor-pointer ${
          dragOver
            ? 'border-[var(--okw-primary)] bg-[var(--okw-primary-light)]'
            : 'border-[var(--okw-border)] hover:border-[var(--okw-primary)]/50'
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload
          size={24}
          className={`mx-auto mb-2 ${dragOver ? 'text-[var(--okw-primary)]' : 'text-[var(--okw-text-muted)]'}`}
        />
        <p className="text-sm font-medium text-[var(--okw-text)]">
          {uploading ? 'Uploading...' : 'Drop files or click to upload'}
        </p>
        <p className="text-xs text-[var(--okw-text-muted)] mt-1">PDF, HTML, Markdown</p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.html,.htm,.md,.txt"
          className="hidden"
          onChange={(e) => onUpload(e.target.files)}
        />
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {docs.length === 0 ? (
          <div className="text-center py-12 text-[var(--okw-text-muted)]">
            <FileText size={32} className="mx-auto mb-2 opacity-40" />
            <p className="text-sm">No documents yet</p>
            <p className="text-xs mt-1">Upload process documents to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            {docs.map((doc, i) => (
              <div
                key={doc.id}
                className={`flex items-center gap-3 p-3 rounded-lg border transition-all cursor-pointer animate-fade-in-up ${
                  selectedDocId === doc.id
                    ? 'border-[var(--okw-primary)] bg-[var(--okw-primary-light)]'
                    : 'border-[var(--okw-border)] hover:border-[var(--okw-primary)]/30 hover:shadow-sm'
                }`}
                style={{ animationDelay: `${i * 50}ms` }}
                onClick={() => onPreview(doc)}
              >
                <span className="text-xl">{mimeIcon(doc.mime_type)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--okw-text)] truncate">
                    {doc.original_filename}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-[var(--okw-text-muted)]">
                      {formatFileSize(doc.file_size_bytes)}
                    </span>
                    {doc.page_count && (
                      <span className="text-xs text-[var(--okw-text-muted)]">
                        {doc.page_count} pages
                      </span>
                    )}
                    <span className={`text-xs px-1.5 py-0.5 rounded ${statusClass(doc.status)}`}>
                      {doc.status}
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(doc.id);
                  }}
                  className="p-1.5 rounded hover:bg-red-50 text-[var(--okw-text-muted)] hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function statusClass(status: string): string {
  if (status === 'ready') return 'bg-green-50 text-green-700';
  if (status === 'processing') return 'bg-yellow-50 text-yellow-700';
  if (status === 'error') return 'bg-red-50 text-red-700';
  return 'bg-gray-50 text-gray-600';
}
