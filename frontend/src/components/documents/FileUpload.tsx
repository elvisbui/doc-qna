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

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  onUploadBatch: (files: File[]) => Promise<void>;
  batchProgress: BatchProgress;
  onClearBatch: () => void;
  isLoading: boolean;
}

function StatusIcon({ status }: { status: 'pending' | 'uploading' | 'done' | 'error' }) {
  switch (status) {
    case 'pending':
      return (
        <svg className="h-4 w-4 text-gray-400 dark:text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <circle cx="12" cy="12" r="10" />
        </svg>
      );
    case 'uploading':
      return (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 dark:border-white/20 border-t-gray-900 dark:border-t-white" />
      );
    case 'done':
      return (
        <svg className="h-4 w-4 text-gray-900 dark:text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      );
    case 'error':
      return (
        <svg className="h-4 w-4 text-gray-500 dark:text-white/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
  }
}

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
        const message = err instanceof Error ? err.message : 'Upload failed.';
        setErrorMessage(message);
        setUploadStatus('error');
      }
    },
    [onUpload],
  );

  const handleFiles = useCallback(
    (files: FileList) => {
      const fileArray = Array.from(files);

      if (fileArray.length === 1 && selectedFiles.length === 0) {
        handleFile(fileArray[0]);
        return;
      }

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

  const dropzoneCls = isDragging
    ? 'border-gray-900 dark:border-white bg-gray-50 dark:bg-white/5'
    : uploadStatus === 'success'
      ? 'border-gray-900 dark:border-white'
      : uploadStatus === 'error'
        ? 'border-gray-400 dark:border-white/30'
        : 'border-gray-200 dark:border-white/10 hover:border-gray-400 dark:hover:border-white/20';

  const isBatchActive = batchProgress.totalCount > 0;

  return (
    <div>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`relative cursor-pointer rounded-xl border border-dashed p-8 text-center transition-colors w-full ${dropzoneCls}`}
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
          <div className="flex flex-col items-center gap-2">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 dark:border-white/20 border-t-gray-900 dark:border-t-white" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Uploading…</p>
          </div>
        ) : uploadStatus === 'success' ? (
          <div className="flex flex-col items-center gap-2">
            <svg className="h-5 w-5 text-gray-900 dark:text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <p className="text-sm text-gray-900 dark:text-gray-100">Uploaded</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <svg
              className="h-6 w-6 text-gray-400 dark:text-white/30 mb-1"
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
            <p className="text-sm text-gray-900 dark:text-gray-100">
              Click to upload or drag and drop
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">PDF, DOCX, MD, TXT</p>
          </div>
        )}
      </div>

      {errorMessage && (
        <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{errorMessage}</p>
      )}

      {selectedFiles.length > 0 && !isBatchActive && (
        <div className="mt-4">
          <div className="flex items-center justify-between py-2">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleClearSelected}
                className="rounded-full px-3 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
              >
                Clear
              </button>
              <button
                onClick={handleUploadAll}
                className="rounded-full bg-gray-900 dark:bg-white px-3.5 py-1.5 text-xs font-medium text-white dark:text-gray-900 hover:opacity-90 transition-opacity"
              >
                Upload all
              </button>
            </div>
          </div>
          <ul className="divide-y divide-gray-200 dark:divide-white/10 border-t border-gray-200 dark:border-white/10">
            {selectedFiles.map((file, index) => (
              <li key={`${file.name}-${index}`} className="flex items-center justify-between py-2">
                <span className="truncate text-sm text-gray-700 dark:text-gray-300">{file.name}</span>
                <button
                  onClick={() => handleRemoveFile(index)}
                  className="ml-2 flex-shrink-0 rounded-lg p-1 text-gray-400 dark:text-white/40 hover:bg-gray-100 dark:hover:bg-white/5 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                  title="Remove file"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {isBatchActive && (
        <div className="mt-4">
          <div className="flex items-center justify-between py-2">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {batchProgress.isRunning
                ? `Uploading ${batchProgress.completedCount} / ${batchProgress.totalCount}`
                : `Done. ${batchProgress.completedCount} / ${batchProgress.totalCount}`}
            </p>
            {!batchProgress.isRunning && (
              <button
                onClick={handleDismissBatch}
                className="rounded-full px-3 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
              >
                Dismiss
              </button>
            )}
          </div>
          <ul className="divide-y divide-gray-200 dark:divide-white/10 border-t border-gray-200 dark:border-white/10">
            {batchProgress.entries.map((entry, index) => (
              <li key={`${entry.file.name}-${index}`} className="flex items-center gap-3 py-2">
                <StatusIcon status={entry.status} />
                <span className="truncate text-sm text-gray-700 dark:text-gray-300">
                  {entry.file.name}
                </span>
                {entry.status === 'error' && entry.errorMessage && (
                  <span className="ml-auto flex-shrink-0 text-xs text-gray-500 dark:text-gray-400">
                    {entry.errorMessage}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
