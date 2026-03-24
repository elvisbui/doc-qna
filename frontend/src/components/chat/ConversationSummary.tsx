import { useState } from 'react';

/** Props for the ConversationSummary component. */
interface ConversationSummaryProps {
  /** The LLM-generated summary of older conversation messages */
  summary: string;
}

/** Collapsible banner showing a summary of older conversation history. */
export function ConversationSummary({ summary }: ConversationSummaryProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="max-w-3xl mx-auto w-full px-4 mt-2 mb-1">
      <div className="rounded-lg border border-gray-100 dark:border-white/10 bg-gray-50/50 dark:bg-white/[0.02]">
        <button
          onClick={() => setIsExpanded((prev) => !prev)}
          className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
        >
          <span>Conversation summary</span>
          <svg
            className={`h-3.5 w-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
        {isExpanded && (
          <div className="px-3 pb-2 text-xs italic text-gray-600 dark:text-gray-300 leading-relaxed">
            {summary}
          </div>
        )}
      </div>
    </div>
  );
}
