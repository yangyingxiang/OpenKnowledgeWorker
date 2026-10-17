'use client';

import { useState, useEffect, useCallback, use } from 'react';
import { api, Document } from '@/lib/api';
import { DocumentList } from '@/components/documents/DocumentList';
import { DocumentPreview, isHtmlDocument } from '@/components/documents/DocumentPreview';

export default function DocumentsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: processId } = use(params);
  const [docs, setDocs] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [previewText, setPreviewText] = useState('');
  const [uploading, setUploading] = useState(false);

  const loadDocs = useCallback(async () => {
    try {
      const data = await api.listDocuments(processId);
      setDocs(data);
    } catch (err) {
      console.error('Failed to load docs:', err);
    }
  }, [processId]);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const handleUpload = async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        await api.uploadDocument(processId, file);
      } catch (err) {
        console.error('Upload failed:', err);
      }
    }
    setUploading(false);
    loadDocs();
  };

  const handleDelete = async (docId: string) => {
    try {
      await api.deleteDocument(processId, docId);
      if (selectedDoc?.id === docId) {
        setSelectedDoc(null);
        setPreviewText('');
      }
      loadDocs();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handlePreview = async (doc: Document) => {
    setSelectedDoc(doc);
    if (!isHtmlDocument(doc)) {
      try {
        const full = await api.getDocument(processId, doc.id);
        setPreviewText(full.extracted_text || 'No extracted text available');
      } catch {
        setPreviewText('Failed to load preview');
      }
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <DocumentList
        docs={docs}
        selectedDocId={selectedDoc?.id}
        uploading={uploading}
        onUpload={handleUpload}
        onPreview={handlePreview}
        onDelete={handleDelete}
      />
      <DocumentPreview
        processId={processId}
        selectedDoc={selectedDoc}
        previewText={previewText}
        onClose={() => {
          setSelectedDoc(null);
          setPreviewText('');
        }}
      />
    </div>
  );
}
