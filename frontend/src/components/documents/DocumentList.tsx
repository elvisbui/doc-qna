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

const STATUS_STYLES: Record<DocumentStatus, string> = {
  pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400',
  processing: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400',
  ready: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
  error: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
};

const STATUS_LABELS: Record<DocumentStatus, string> = {
  pending: 'Pending',
  processing: 'Processing',
  ready: 'Ready',
  error: 'Error',
};

/** 6-dot grip icon used as a drag handle. */
function DragHandle() {
  return (
    <svg
      className="h-5 w-5 text-gray-300 dark:text-gray-600 group-hover:text-gray-500 dark:group-hover:text-gray-400 transition-colors"
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

/** Props for the DocumentList component. */
interface DocumentListProps {
  /** Array of uploaded documents to display */
  documents: Document[];
  /** Callback to delete a document by ID */
  onDelete: (id: string) => Promise<void>;
  /** Callback to reorder documents via drag-and-drop */
  onReorder: (fromIndex: number, toIndex: number) => void;
  /** Whether the document list is currently loading */
  isLoading: boolean;
}

/** Sortable list of uploaded documents with status badges, preview, and delete controls. */
export function DocumentList({ documents, onDelete, onReorder, isLoading }: DocumentListProps) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<{ id: string; filename: string } | null>(null);

  // Drag-and-drop state
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

  // --- Drag-and-drop handlers ---

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
        title="No documents uploaded yet"
        description="Upload a document to get started."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <ul className="divide-y divide-gray-200 dark:divide-gray-700">
        {documents.map((doc, index) => (
          <li
            key={doc.id}
            draggable
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDrop={(e) => handleDrop(e, index)}
            onDragEnd={handleDragEnd}
            onDragLeave={handleDragLeave}
            className={`group flex flex-col sm:flex-row sm:items-center justify-between px-4 py-3 gap-2 sm:gap-0 transition-all hover:bg-gray-50 dark:hover:bg-gray-750 ${
              draggingIndex === index ? 'opacity-50' : ''
            } ${
              dragOverIndex === index && draggingIndex !== index
                ? 'border-2 border-blue-400 dark:border-blue-500'
                : ''
            }`}
          >
            {/* Drag handle */}
            <div className="mr-3 flex shrink-0 cursor-grab items-center active:cursor-grabbing">
              <DragHandle />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3 flex-wrap">
                <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                  {doc.filename}
                </p>
                <span
                  className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[doc.status]}`}
                >
                  {STATUS_LABELS[doc.status]}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                <span>{doc.fileType.replace(/^\./, '').toUpperCase()}</span>
                <span className="hidden sm:inline">{formatFileSize(doc.fileSize)}</span>
                {doc.errorMessage && (
                  <span className="text-red-600 dark:text-red-400" title={doc.errorMessage}>
                    {doc.errorMessage}
                  </span>
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2 sm:ml-4 self-end sm:self-center">
              <button
                onClick={() => setPreviewDoc({ id: doc.id, filename: doc.filename })}
                className="rounded-lg p-1.5 text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                title="Preview document"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
              </button>
              {confirmingId === doc.id ? (
                <>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="rounded-lg px-2.5 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 transition-colors"
                  >
                    {deletingId === doc.id ? 'Deleting...' : 'Confirm'}
                  </button>
                  <button
                    onClick={handleCancelDelete}
                    className="rounded-lg px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="rounded-lg p-1.5 text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  title="Delete document"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
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
    </div>
  );
}
