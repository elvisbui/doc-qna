import { useState, useRef, useCallback } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void | Promise<void>;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setValue(e.target.value);
      const textarea = e.target;
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    },
    [],
  );

  const canSend = value.trim().length > 0 && !isLoading;

  return (
    <div className="max-w-3xl mx-auto w-full px-4 pb-4 pt-2">
      <div className="flex items-end rounded-3xl border border-gray-200 dark:border-white/15 bg-white dark:bg-[#2f2f2f] focus-within:border-gray-400 dark:focus-within:border-white/25 transition-colors">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Message"
          disabled={isLoading}
          rows={1}
          className="flex-1 resize-none bg-transparent pl-5 pr-2 py-3.5 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <div className="flex-shrink-0 pr-2 pb-2">
          <button
            onClick={handleSubmit}
            disabled={!canSend}
            className={`flex items-center justify-center w-8 h-8 rounded-full transition-all ${
              canSend
                ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90'
                : 'bg-gray-200 dark:bg-white/10 text-gray-400 dark:text-white/30 cursor-not-allowed'
            }`}
            aria-label="Send message"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5m0 0l-7 7m7-7l7 7" />
            </svg>
          </button>
        </div>
      </div>
      <p className="text-center text-[11px] text-gray-400 dark:text-gray-500 mt-2">
        Answers are drawn from your uploaded documents only.
      </p>
    </div>
  );
}
