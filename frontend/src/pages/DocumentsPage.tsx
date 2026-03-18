import { useEffect, useCallback } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import { FileUpload } from '@/components/documents/FileUpload';
import { DocumentList } from '@/components/documents/DocumentList';
import type { ToastType } from '@/hooks/useToast';

/** Props for the DocumentsPage component. */
interface DocumentsPageProps {
  /** Function to display a toast notification */
  addToast: (type: ToastType, message: string) => string;
  /** Whether this page tab is currently visible (controls polling) */
  isActive?: boolean;
}

/** Page for uploading, listing, and managing documents. */
export function DocumentsPage({ addToast, isActive }: DocumentsPageProps) {
  const { documents, isLoading, error, upload, uploadBatch, batchProgress, clearBatch, refresh, deleteDocument, reorderDocuments } = useDocuments();

  useEffect(() => {
    if (isActive !== false) {
      refresh();
    }
  }, [refresh, isActive]);

  // Poll while any document is still processing
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
        addToast('success', `"${file.name}" uploaded successfully.`);
      } else {
        addToast('error', `Failed to upload "${file.name}".`);
      }
    },
    [upload, addToast],
  );

  const handleUploadBatch = useCallback(
    async (files: File[]) => {
      const result = await uploadBatch(files);
      if (result.completedCount === result.totalCount) {
        addToast('success', `All ${result.totalCount} files uploaded successfully.`);
      } else {
        addToast('info', `${result.completedCount} of ${result.totalCount} files uploaded.`);
      }
    },
    [uploadBatch, addToast],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      const success = await deleteDocument(id);
      if (success) {
        addToast('success', 'Document deleted successfully.');
      } else {
        addToast('error', 'Failed to delete document.');
      }
    },
    [deleteDocument, addToast],
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:py-8 w-full animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Documents</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Upload and manage your documents for Q&A.
        </p>
      </div>

      <div className="mb-6">
        <FileUpload
          onUpload={handleUpload}
          onUploadBatch={handleUploadBatch}
          batchProgress={batchProgress}
          onClearBatch={clearBatch}
          isLoading={isLoading}
        />
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Uploaded Documents</h2>
        <button
          onClick={refresh}
          disabled={isLoading}
          className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {isLoading ? 'Refreshing...' : 'Refresh'}
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
