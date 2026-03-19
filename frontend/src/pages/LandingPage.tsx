import { useState, useRef, useCallback } from 'react';
import { uploadDocument } from '@/lib/api';
import { AppAvatar } from '@/components/ui/Avatar';

/** Props for the LandingPage component. */
interface LandingPageProps {
  /** Callback to navigate to the chat page with an initial query */
  onNavigateToChat: (query: string) => void;
  /** Callback to navigate to the documents page after a file upload */
  onNavigateToDocuments?: () => void;
}

/** Hero landing page with a centered search input and quick file upload. */
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
        // silently fail — user can retry from Documents page
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
        {/* Hero */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3">
            <AppAvatar size="lg" />
          </div>
          <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Ask Your Documents Anything
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-lg mx-auto">
            Upload your documents and get accurate, cited answers. Every response is grounded in your data.
          </p>
        </div>

        {/* Input area */}
        <div className="relative rounded-2xl border border-gray-200 dark:border-white/15 bg-white dark:bg-[#303030] shadow-sm">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything"
            rows={1}
            className="w-full resize-none bg-transparent px-14 py-4 text-base text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none"
            style={{ minHeight: '56px', maxHeight: '200px' }}
          />

          {/* Attach file button (left) */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-full text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-black/5 dark:hover:bg-white/10 transition-colors disabled:opacity-50"
            title="Upload a document"
          >
            {isUploading ? (
              <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
            )}
          </button>

          {/* Send button (right) */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!query.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black dark:bg-white text-white dark:text-black disabled:opacity-30 transition-opacity"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          </button>

          {/* Hidden file input */}
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
