import { useState } from 'react';

interface ConversationSummaryProps {
  summary: string;
}

export function ConversationSummary({ summary }: ConversationSummaryProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="max-w-3xl mx-auto w-full px-4 pt-2">
      <button
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between py-2 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
      >
        <span>Earlier summary</span>
        <svg
          className={`h-3.5 w-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {isExpanded && (
        <p className="pb-2 text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
          {summary}
        </p>
      )}
    </div>
  );
}
