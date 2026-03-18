import { useState, useRef, useCallback } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import type { BatchProgress } from '@/hooks/useDocuments';

const ACCEPTED_TYPES: Record<string, string> = {
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
  'text/markdown': '.md',
  'text/plain': '.txt',
};

const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.md', '.txt'];

function isValidFile(file: File): boolean {
  if (ACCEPTED_TYPES[file.type]) return true;
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  return ACCEPTED_EXTENSIONS.includes(ext);
}

/** Props for the FileUpload component. */
interface FileUploadProps {
  /** Callback to upload a single file */
  onUpload: (file: File) => Promise<void>;
  /** Callback to upload multiple files as a batch */
  onUploadBatch: (files: File[]) => Promise<void>;
  /** Current batch upload progress state */
  batchProgress: BatchProgress;
  /** Callback to dismiss the batch progress display */
  onClearBatch: () => void;
  /** Whether an upload is currently in progress */
  isLoading: boolean;
}

function StatusIcon({ status }: { status: 'pending' | 'uploading' | 'done' | 'error' }) {
  switch (status) {
    case 'pending':
      return (
        <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" />
        </svg>
      );
    case 'uploading':
      return (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      );
    case 'done':
      return (
        <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      );
    case 'error':
      return (
        <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
  }
}

/** Drag-and-drop file upload zone with single and batch upload support. */
export function FileUpload({ onUpload, onUploadBatch, batchProgress, onClearBatch, isLoading }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!isValidFile(file)) {
        setErrorMessage(`Unsupported file type. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`);
        setUploadStatus('error');
        return;
      }

      setUploadStatus('uploading');
      setErrorMessage(null);

      try {
        await onUpload(file);
        setUploadStatus('success');
        setTimeout(() => setUploadStatus('idle'), 2000);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Upload failed';
        setErrorMessage(message);
        setUploadStatus('error');
      }
    },
    [onUpload],
  );

  const handleFiles = useCallback(
    (files: FileList) => {
      const fileArray = Array.from(files);

      // If single file and no batch in progress, use the original single-file flow
      if (fileArray.length === 1 && selectedFiles.length === 0) {
        handleFile(fileArray[0]);
        return;
      }

      // For multiple files, add to the selected files list for batch upload
      const validFiles: File[] = [];
      const invalidNames: string[] = [];

      for (const file of fileArray) {
        if (isValidFile(file)) {
          validFiles.push(file);
        } else {
          invalidNames.push(file.name);
        }
      }

      if (invalidNames.length > 0) {
        setErrorMessage(
          `Skipped unsupported files: ${invalidNames.join(', ')}. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`,
        );
      } else {
        setErrorMessage(null);
      }

      if (validFiles.length > 0) {
        setSelectedFiles((prev) => [...prev, ...validFiles]);
      }
    },
    [handleFile, selectedFiles.length],
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles],
  );

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files);
      }
      // Reset so the same file can be re-selected
      e.target.value = '';
    },
    [handleFiles],
  );

  const handleUploadAll = useCallback(async () => {
    if (selectedFiles.length === 0) return;
    const filesToUpload = [...selectedFiles];
    setSelectedFiles([]);
    setErrorMessage(null);
    await onUploadBatch(filesToUpload);
  }, [selectedFiles, onUploadBatch]);

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleClearSelected = useCallback(() => {
    setSelectedFiles([]);
    setErrorMessage(null);
  }, []);

  const handleDismissBatch = useCallback(() => {
    onClearBatch();
  }, [onClearBatch]);

  const borderColor = isDragging
    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
    : uploadStatus === 'success'
      ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
      : uploadStatus === 'error'
        ? 'border-red-400 bg-red-50 dark:bg-red-900/20'
        : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500';

  const isBatchActive = batchProgress.totalCount > 0;

  return (
    <div>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`relative cursor-pointer rounded-lg border-2 border-dashed p-4 sm:p-8 text-center transition-colors w-full ${borderColor}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS.join(',')}
          onChange={handleChange}
          className="hidden"
        />

        {uploadStatus === 'uploading' || isLoading ? (
          <div className="space-y-2">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-gray-300 dark:border-gray-600 border-t-blue-600" />
            <p className="text-sm text-gray-600 dark:text-gray-400">Uploading...</p>
          </div>
        ) : uploadStatus === 'success' ? (
          <div className="space-y-2">
            <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-sm text-green-700 dark:text-green-400">Upload successful!</p>
          </div>
        ) : (
          <div className="space-y-2">
            <svg
              className="mx-auto h-10 w-10 text-gray-400 dark:text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 16v-8m0 0l-3 3m3-3l3 3M6.75 19.25h10.5A2.25 2.25 0 0019.5 17V7a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 7v10c0 1.243 1.007 2.25 2.25 2.25z"
              />
            </svg>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              <span className="font-semibold text-blue-600 dark:text-blue-400">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500">PDF, DOCX, MD, TXT — select multiple files for batch upload</p>
          </div>
        )}
      </div>

      {errorMessage && (
        <p className="mt-2 text-sm text-red-600">{errorMessage}</p>
      )}

      {/* Selected files list (before upload) */}
      {selectedFiles.length > 0 && !isBatchActive && (
        <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-4 py-3">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleClearSelected}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Clear
              </button>
              <button
                onClick={handleUploadAll}
                className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 transition-colors"
              >
                Upload All
              </button>
            </div>
          </div>
          <ul className="divide-y divide-gray-100 dark:divide-gray-700">
            {selectedFiles.map((file, index) => (
              <li key={`${file.name}-${index}`} className="flex items-center justify-between px-4 py-2">
                <span className="truncate text-sm text-gray-600 dark:text-gray-400">{file.name}</span>
                <button
                  onClick={() => handleRemoveFile(index)}
                  className="ml-2 flex-shrink-0 rounded-lg p-1 text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  title="Remove file"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Batch progress (during/after upload) */}
      {isBatchActive && (
        <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-4 py-3">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {batchProgress.isRunning
                ? `Uploading: ${batchProgress.completedCount} of ${batchProgress.totalCount} uploaded`
                : `Done: ${batchProgress.completedCount} of ${batchProgress.totalCount} uploaded`}
            </p>
            {!batchProgress.isRunning && (
              <button
                onClick={handleDismissBatch}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Dismiss
              </button>
            )}
          </div>
          <ul className="divide-y divide-gray-100 dark:divide-gray-700">
            {batchProgress.entries.map((entry, index) => (
              <li key={`${entry.file.name}-${index}`} className="flex items-center gap-3 px-4 py-2">
                <StatusIcon status={entry.status} />
                <span className={`truncate text-sm ${entry.status === 'error' ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-400'}`}>
                  {entry.file.name}
                </span>
                {entry.status === 'error' && entry.errorMessage && (
                  <span className="ml-auto flex-shrink-0 text-xs text-red-500 dark:text-red-400">{entry.errorMessage}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
