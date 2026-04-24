import { useState, useRef, useCallback } from 'react';
import { uploadDocument } from '@/lib/api';

interface LandingPageProps {
  onNavigateToChat: (query: string) => void;
  onNavigateToDocuments?: () => void;
}

export function LandingPage({ onNavigateToChat, onNavigateToDocuments }: LandingPageProps) {
  const [query, setQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed) return;
    setQuery('');
    onNavigateToChat(trimmed);
  }, [query, onNavigateToChat]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      setIsUploading(true);
      try {
        await uploadDocument(file);
        onNavigateToDocuments?.();
      } catch {
        // Retry possible from Documents page.
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    },
    [onNavigateToDocuments],
  );

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 bg-white dark:bg-[#212121] min-h-full">
      <div className="w-full max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-100">
            doc-qna
          </h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Upload a document and ask a question.
          </p>
        </div>

        <div className="relative rounded-3xl border border-gray-200 dark:border-white/15 bg-white dark:bg-[#2f2f2f] focus-within:border-gray-400 dark:focus-within:border-white/25 transition-colors">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message"
            rows={1}
            className="w-full resize-none bg-transparent pl-14 pr-14 py-4 text-base text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none"
            style={{ minHeight: '56px', maxHeight: '200px' }}
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-full text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-black/5 dark:hover:bg-white/10 transition-colors disabled:opacity-50"
            title="Upload a document"
            aria-label="Upload a document"
          >
            {isUploading ? (
              <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            )}
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!query.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-30 transition-opacity"
            aria-label="Send"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5m0 0l-7 7m7-7l7 7" />
            </svg>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.docx,.doc,.md,.txt"
            className="hidden"
          />
        </div>
      </div>
    </div>
  );
}
