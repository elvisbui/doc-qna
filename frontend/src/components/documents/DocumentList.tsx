import { useState, useRef } from 'react';
import type { Document, DocumentStatus } from '@/types';
import { DocumentListSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { DocumentPreview } from '@/components/documents/DocumentPreview';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const STATUS_LABELS: Record<DocumentStatus, string> = {
  pending: 'Pending',
  processing: 'Processing',
  ready: 'Ready',
  error: 'Error',
};

function StatusDot({ status }: { status: DocumentStatus }) {
  const cls = {
    pending: 'bg-gray-300 dark:bg-white/25',
    processing: 'bg-gray-400 dark:bg-white/40 animate-pulse',
    ready: 'bg-gray-900 dark:bg-white',
    error: 'bg-gray-900 dark:bg-white ring-2 ring-gray-900/10 dark:ring-white/10',
  }[status];
  return <span className={`inline-block h-1.5 w-1.5 rounded-full ${cls}`} aria-hidden="true" />;
}

function DragHandle() {
  return (
    <svg
      className="h-5 w-5 text-gray-300 dark:text-white/20 group-hover:text-gray-500 dark:group-hover:text-white/40 transition-colors"
      viewBox="0 0 16 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <circle cx="5" cy="3" r="1.5" />
      <circle cx="11" cy="3" r="1.5" />
      <circle cx="5" cy="10" r="1.5" />
      <circle cx="11" cy="10" r="1.5" />
      <circle cx="5" cy="17" r="1.5" />
      <circle cx="11" cy="17" r="1.5" />
    </svg>
  );
}

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: string) => Promise<void>;
  onReorder: (fromIndex: number, toIndex: number) => void;
  isLoading: boolean;
}

export function DocumentList({ documents, onDelete, onReorder, isLoading }: DocumentListProps) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<{ id: string; filename: string } | null>(null);

  const dragIndexRef = useRef<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);

  const handleDelete = async (id: string) => {
    if (confirmingId !== id) {
      setConfirmingId(id);
      return;
    }

    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
      setConfirmingId(null);
    }
  };

  const handleCancelDelete = () => {
    setConfirmingId(null);
  };

  const handleDragStart = (index: number) => {
    dragIndexRef.current = index;
    setDraggingIndex(index);
  };

  const handleDragOver = (e: React.DragEvent<HTMLLIElement>, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  const handleDrop = (e: React.DragEvent<HTMLLIElement>, toIndex: number) => {
    e.preventDefault();
    const fromIndex = dragIndexRef.current;
    if (fromIndex !== null && fromIndex !== toIndex) {
      onReorder(fromIndex, toIndex);
    }
    dragIndexRef.current = null;
    setDragOverIndex(null);
    setDraggingIndex(null);
  };

  const handleDragEnd = () => {
    dragIndexRef.current = null;
    setDragOverIndex(null);
    setDraggingIndex(null);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  if (isLoading && documents.length === 0) {
    return <DocumentListSkeleton />;
  }

  if (documents.length === 0) {
    return (
      <EmptyState
        title="No documents yet"
        description="Upload a PDF, DOCX, Markdown, or text file to get started."
      />
    );
  }

  return (
    <>
      <ul className="divide-y divide-gray-200 dark:divide-white/10 border-t border-gray-200 dark:border-white/10">
        {documents.map((doc, index) => (
          <li
            key={doc.id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDrop={(e) => handleDrop(e, index)}
            onDragEnd={handleDragEnd}
            onDragLeave={handleDragLeave}
            className={`group flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-0 py-3 transition-all ${
              draggingIndex === index ? 'opacity-50' : ''
            } ${
              dragOverIndex === index && draggingIndex !== index
                ? 'bg-gray-50 dark:bg-white/5'
                : ''
            }`}
          >
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="shrink-0 cursor-grab active:cursor-grabbing">
                <DragHandle />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="truncate text-sm text-gray-900 dark:text-gray-100">
                    {doc.filename}
                  </p>
                  <span className="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                    <StatusDot status={doc.status} />
                    {STATUS_LABELS[doc.status]}
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                  <span>{doc.fileType.replace(/^\./, '').toUpperCase()}</span>
                  <span className="hidden sm:inline">{formatFileSize(doc.fileSize)}</span>
                  {doc.errorMessage && (
                    <span title={doc.errorMessage} className="truncate">
                      {doc.errorMessage}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-1 sm:ml-4 self-end sm:self-center">
              <button
                onClick={() => setPreviewDoc({ id: doc.id, filename: doc.filename })}
                className="rounded-lg p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                title="Preview"
                aria-label={`Preview ${doc.filename}`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
              {confirmingId === doc.id ? (
                <>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="rounded-full px-2.5 py-1 text-xs font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 disabled:opacity-40 transition-opacity"
                  >
                    {deletingId === doc.id ? 'Deleting…' : 'Confirm'}
                  </button>
                  <button
                    onClick={handleCancelDelete}
                    className="rounded-full px-2.5 py-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="rounded-lg p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                  title="Delete"
                  aria-label={`Delete ${doc.filename}`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {previewDoc && (
        <DocumentPreview
          documentId={previewDoc.id}
          filename={previewDoc.filename}
          onClose={() => setPreviewDoc(null)}
        />
      )}
    </>
  );
}
