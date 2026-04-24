import { useEffect, useState } from 'react';
import { getDocumentPreview } from '@/lib/api';
import type { DocumentPreview as DocumentPreviewType } from '@/types';

interface DocumentPreviewProps {
  documentId: string;
  filename: string;
  onClose: () => void;
}

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
          setError(err instanceof Error ? err.message : 'Could not load preview.');
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
      <div
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px]"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white dark:bg-[#212121] border-l border-gray-200 dark:border-white/10">
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-white/10 px-4 py-3">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
              {filename}
            </h2>
            {preview && (
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {preview.totalLength.toLocaleString()} characters
                {preview.truncated && ' · showing first 5,000'}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 rounded-lg p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            title="Close"
            aria-label="Close preview"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {isLoading && (
            <div className="flex items-center justify-center py-12 gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 dark:border-white/20 border-t-gray-900 dark:border-t-white" />
              <span className="text-sm text-gray-500 dark:text-gray-400">Loading…</span>
            </div>
          )}

          {error && (
            <p className="text-sm text-gray-700 dark:text-gray-300">{error}</p>
          )}

          {preview && !isLoading && (
            <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-800 dark:text-gray-200 font-mono">
              {preview.content}
            </pre>
          )}
        </div>

        {preview?.truncated && !isLoading && (
          <div className="border-t border-gray-200 dark:border-white/10 px-4 py-2 text-center text-xs text-gray-500 dark:text-gray-400">
            Truncated. Showing first 5,000 of {preview.totalLength.toLocaleString()} characters.
          </div>
        )}
      </div>
    </>
  );
}
