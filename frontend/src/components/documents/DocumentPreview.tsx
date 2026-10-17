'use client';

import { Eye, File, X } from 'lucide-react';
import type { Document } from '@/lib/api';
import { DocumentRenderer } from './DocumentRenderer';

export const isHtmlDocument = (doc: Document) => doc.mime_type.includes('html');

/**
 * Right column of the Documents page. HTML documents are shown in an iframe served by the
 * backend; everything else is shown as rendered extracted text.
 */
export function DocumentPreview({
  processId,
  selectedDoc,
  previewText,
  onClose,
}: {
  processId: string;
  selectedDoc: Document | null;
  previewText: string;
  onClose: () => void;
}) {
  return (
    <div className="flex-1 flex flex-col bg-[var(--okw-bg)]">
      {selectedDoc ? (
        <>
          <div className="px-6 py-3 border-b border-[var(--okw-border)] bg-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eye size={16} className="text-[var(--okw-primary)]" />
              <span className="text-sm font-medium text-[var(--okw-text)]">
                {selectedDoc.original_filename}
              </span>
            </div>
            <button onClick={onClose} className="p-1 rounded hover:bg-[var(--okw-bg)]">
              <X size={16} className="text-[var(--okw-text-muted)]" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {isHtmlDocument(selectedDoc) ? (
              <iframe
                src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5003'}/api/processes/${processId}/documents/${selectedDoc.id}/content`}
                className="w-full h-full border-0"
                title={selectedDoc.original_filename}
              />
            ) : (
              <DocumentRenderer
                text={previewText}
                filename={selectedDoc.original_filename}
                documentId={selectedDoc.id}
              />
            )}
          </div>
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-[var(--okw-text-muted)]">
            <File size={40} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Select a document to preview</p>
          </div>
        </div>
      )}
    </div>
  );
}
