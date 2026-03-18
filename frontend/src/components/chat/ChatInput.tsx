import { useState, useRef, useCallback } from 'react';

/** Props for the ChatInput component. */
interface ChatInputProps {
  /** Callback invoked with the trimmed message text when the user submits */
  onSend: (message: string) => void | Promise<void>;
  /** Whether a chat response is currently streaming (disables input) */
  isLoading: boolean;
}

/** Auto-resizing textarea input for composing and sending chat messages. */
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
      <div className="flex items-end rounded-full border border-gray-200 dark:border-white/15 bg-white dark:bg-[#303030] shadow-sm focus-within:border-gray-300 dark:focus-within:border-white/25 transition-colors">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything"
          disabled={isLoading}
          rows={1}
          className="flex-1 resize-none bg-transparent pl-5 pr-2 py-3 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <div className="flex-shrink-0 pr-2 pb-1.5">
          <button
            onClick={handleSubmit}
            disabled={!canSend}
            className={`flex items-center justify-center w-8 h-8 rounded-full transition-all ${
              canSend
                ? 'bg-black dark:bg-white text-white dark:text-black hover:opacity-80'
                : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
            }`}
            aria-label="Send message"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </div>
      </div>
      <p className="text-center text-[11px] text-gray-400 dark:text-gray-500 mt-2">
        Press Enter to send, Shift+Enter for a new line
      </p>
    </div>
  );
}
