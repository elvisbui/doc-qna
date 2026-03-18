import { useState, useCallback } from 'react';
import type { Document } from '@/types';
import {
  getDocuments,
  uploadDocument,
  deleteDocument as deleteDocumentApi,
} from '@/lib/api';

/** Status of an individual file within a batch upload. */
export type FileUploadStatus = 'pending' | 'uploading' | 'done' | 'error';

/** Tracks a single file's upload state within a batch. */
export interface BatchFileEntry {
  /** The File object being uploaded. */
  file: File;
  /** Current upload status of this file. */
  status: FileUploadStatus;
  /** Error details if the upload failed. */
  errorMessage?: string;
}

/** Progress state for an ongoing batch upload operation. */
export interface BatchProgress {
  /** Upload state of each file in the batch. */
  entries: BatchFileEntry[];
  /** Number of files that have been successfully uploaded. */
  completedCount: number;
  /** Total number of files in the batch. */
  totalCount: number;
  /** Whether the batch upload is still in progress. */
  isRunning: boolean;
}

/** Return value of the useDocuments hook. */
interface UseDocumentsReturn {
  /** List of all uploaded documents. */
  documents: Document[];
  /** Whether a document operation is in progress. */
  isLoading: boolean;
  /** Error message from the most recent failed operation, if any. */
  error: string | null;
  /** Upload a single file and refresh the document list. */
  upload: (file: File) => Promise<boolean>;
  /** Upload multiple files sequentially, tracking progress per file. */
  uploadBatch: (files: File[]) => Promise<{ completedCount: number; totalCount: number }>;
  /** Current batch upload progress state. */
  batchProgress: BatchProgress;
  /** Reset batch progress state to empty. */
  clearBatch: () => void;
  /** Re-fetch the document list from the API. */
  refresh: () => Promise<void>;
  /** Delete a document by ID and refresh the list. */
  deleteDocument: (id: string) => Promise<boolean>;
  /** Reorder documents in the local list by moving an item between indices. */
  reorderDocuments: (fromIndex: number, toIndex: number) => void;
}

const EMPTY_BATCH: BatchProgress = {
  entries: [],
  completedCount: 0,
  totalCount: 0,
  isRunning: false,
};

/**
 * Manages document CRUD operations including single and batch uploads.
 * @returns Document list, loading state, and action methods.
 */
export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress>(EMPTY_BATCH);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to fetch documents';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const upload = useCallback(
    async (file: File): Promise<boolean> => {
      setIsLoading(true);
      setError(null);
      try {
        await uploadDocument(file);
        await refresh();
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Failed to upload document';
        setError(message);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [refresh],
  );

  const uploadBatch = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return { completedCount: 0, totalCount: 0 };

      const entries: BatchFileEntry[] = files.map((file) => ({
        file,
        status: 'pending' as FileUploadStatus,
      }));

      setBatchProgress({
        entries: [...entries],
        completedCount: 0,
        totalCount: files.length,
        isRunning: true,
      });

      let completedCount = 0;

      for (let i = 0; i < entries.length; i++) {
        // Mark current file as uploading
        entries[i] = { ...entries[i], status: 'uploading' };
        setBatchProgress({
          entries: [...entries],
          completedCount,
          totalCount: files.length,
          isRunning: true,
        });

        try {
          await uploadDocument(entries[i].file);
          entries[i] = { ...entries[i], status: 'done' };
          completedCount++;
        } catch (err) {
          const message =
            err instanceof Error ? err.message : 'Upload failed';
          entries[i] = { ...entries[i], status: 'error', errorMessage: message };
          // Skip failed files and continue with the rest
        }

        setBatchProgress({
          entries: [...entries],
          completedCount,
          totalCount: files.length,
          isRunning: i < entries.length - 1,
        });
      }

      // Final state
      setBatchProgress({
        entries: [...entries],
        completedCount,
        totalCount: files.length,
        isRunning: false,
      });

      // Refresh the document list after batch completes
      await refresh();

      return { completedCount, totalCount: files.length };
    },
    [refresh],
  );

  const clearBatch = useCallback(() => {
    setBatchProgress(EMPTY_BATCH);
  }, []);

  const deleteDoc = useCallback(
    async (id: string): Promise<boolean> => {
      setIsLoading(true);
      setError(null);
      try {
        await deleteDocumentApi(id);
        await refresh();
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Failed to delete document';
        setError(message);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [refresh],
  );

  const reorderDocuments = useCallback(
    (fromIndex: number, toIndex: number) => {
      setDocuments((prev) => {
        if (
          fromIndex < 0 ||
          toIndex < 0 ||
          fromIndex >= prev.length ||
          toIndex >= prev.length ||
          fromIndex === toIndex
        ) {
          return prev;
        }
        const updated = [...prev];
        const [moved] = updated.splice(fromIndex, 1);
        updated.splice(toIndex, 0, moved);
        return updated;
      });
    },
    [],
  );

  return {
    documents,
    isLoading,
    error,
    upload,
    uploadBatch,
    batchProgress,
    clearBatch,
    refresh,
    deleteDocument: deleteDoc,
    reorderDocuments,
  };
}
