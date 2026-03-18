import { useEffect, useState } from 'react';
import { getDocumentPreview } from '@/lib/api';
import type { DocumentPreview as DocumentPreviewType } from '@/types';

/** Props for the DocumentPreview component. */
interface DocumentPreviewProps {
  /** The document ID to fetch the preview for */
  documentId: string;
  /** The document filename to display in the header */
  filename: string;
  /** Callback to close the preview panel */
  onClose: () => void;
}

/** Slide-out panel displaying a text preview of a document's content. */
export function DocumentPreview({ documentId, filename, onClose }: DocumentPreviewProps) {
  const [preview, setPreview] = useState<DocumentPreviewType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchPreview() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getDocumentPreview(documentId);
        if (!cancelled) {
          setPreview(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load preview');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchPreview();
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
      />

      {/* Slide-out panel */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-semibold text-gray-900">
              {filename}
            </h2>
            {preview && (
              <p className="mt-0.5 text-xs text-gray-500">
                {preview.totalLength.toLocaleString()} characters
                {preview.truncated && ' (showing first 5,000)'}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 rounded p-1 text-gray-400 hover:text-gray-600 transition-colors"
            title="Close preview"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
              <span className="ml-2 text-sm text-gray-500">Loading preview...</span>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {preview && !isLoading && (
            <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-800 font-mono">
              {preview.content}
            </pre>
          )}
        </div>

        {/* Footer */}
        {preview?.truncated && !isLoading && (
          <div className="border-t border-gray-200 px-4 py-2 text-center text-xs text-gray-500">
            Content truncated. Showing first 5,000 of {preview.totalLength.toLocaleString()} characters.
          </div>
        )}
      </div>
    </>
  );
}
