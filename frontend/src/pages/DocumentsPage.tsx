import { useEffect, useCallback } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import { FileUpload } from '@/components/documents/FileUpload';
import { DocumentList } from '@/components/documents/DocumentList';
import type { ToastType } from '@/hooks/useToast';

interface DocumentsPageProps {
  addToast: (type: ToastType, message: string) => string;
  isActive?: boolean;
}

export function DocumentsPage({ addToast, isActive }: DocumentsPageProps) {
  const { documents, isLoading, error, upload, uploadBatch, batchProgress, clearBatch, refresh, deleteDocument, reorderDocuments } = useDocuments();

  useEffect(() => {
    if (isActive !== false) {
      refresh();
    }
  }, [refresh, isActive]);

  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === 'processing' || d.status === 'pending');
    if (!hasProcessing || isActive === false) return;

    const interval = setInterval(refresh, 2000);
    return () => clearInterval(interval);
  }, [documents, refresh, isActive]);

  const handleUpload = useCallback(
    async (file: File) => {
      const success = await upload(file);
      if (success) {
        addToast('success', `Uploaded "${file.name}".`);
      } else {
        addToast('error', `Could not upload "${file.name}".`);
      }
    },
    [upload, addToast],
  );

  const handleUploadBatch = useCallback(
    async (files: File[]) => {
      const result = await uploadBatch(files);
      if (result.completedCount === result.totalCount) {
        addToast('success', `Uploaded ${result.totalCount} files.`);
      } else {
        addToast('info', `${result.completedCount} of ${result.totalCount} uploaded.`);
      }
    },
    [uploadBatch, addToast],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      const success = await deleteDocument(id);
      if (success) {
        addToast('success', 'Document deleted.');
      } else {
        addToast('error', 'Could not delete document.');
      }
    },
    [deleteDocument, addToast],
  );

  return (
    <div className="mx-auto max-w-2xl px-4 sm:px-6 py-10 w-full animate-fade-in">
      <header className="mb-8">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Documents
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Upload PDF, DOCX, Markdown, or text files. You can query them from the chat.
        </p>
      </header>

      <div className="mb-8">
        <FileUpload
          onUpload={handleUpload}
          onUploadBatch={handleUploadBatch}
          batchProgress={batchProgress}
          onClearBatch={clearBatch}
          isLoading={isLoading}
        />
      </div>

      {error && (
        <p className="mb-4 text-sm text-gray-700 dark:text-gray-300">{error}</p>
      )}

      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100">Uploaded</h2>
        <button
          onClick={refresh}
          disabled={isLoading}
          className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-40 transition-colors"
        >
          {isLoading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      <DocumentList
        documents={documents}
        onDelete={handleDelete}
        onReorder={reorderDocuments}
        isLoading={isLoading}
      />
    </div>
  );
}
