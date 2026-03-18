import { useState, useEffect, useRef } from 'react';
import type { Citation } from '@/types';

/** Props for the CitationPanel component. */
interface CitationPanelProps {
  /** Array of citation objects to display */
  citations: Citation[];
  /** 1-based index of the citation to highlight (from inline citation click) */
  highlightedIndex?: number | null;
}

/** Collapsible panel displaying source citations with relevance scores. */
export function CitationPanel({ citations, highlightedIndex }: CitationPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (highlightedIndex != null) {
      setIsExpanded(true);
    }
  }, [highlightedIndex]);

  if (citations.length === 0) return null;

  return (
    <div className="max-w-3xl mx-auto w-full border-t border-gray-100 dark:border-white/5 sm:relative fixed bottom-0 left-0 right-0 sm:left-auto sm:right-auto sm:bottom-auto z-10 max-h-[60vh] sm:max-h-none overflow-y-auto bg-white dark:bg-[#212121] shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] sm:shadow-none">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
      >
        <span className="flex items-center gap-2">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
          Sources ({citations.length})
        </span>
        <svg
          className={`h-4 w-4 text-gray-400 dark:text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 space-y-2 animate-fade-in">
          {citations.map((citation, index) => (
            <CitationCard key={index} citation={citation} index={index} isHighlighted={highlightedIndex === index + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface CitationCardProps {
  citation: Citation;
  index: number;
  isHighlighted?: boolean;
}

const CONTENT_PREVIEW_LENGTH = 150;

function CitationCard({ citation, index, isHighlighted }: CitationCardProps) {
  const [isContentExpanded, setIsContentExpanded] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const scorePercent = Math.round(citation.relevanceScore * 100);

  useEffect(() => {
    if (isHighlighted && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [isHighlighted]);

  const previewContent =
    citation.chunkContent.length > CONTENT_PREVIEW_LENGTH
      ? `${citation.chunkContent.slice(0, CONTENT_PREVIEW_LENGTH)}...`
      : citation.chunkContent;

  return (
    <div
      ref={cardRef}
      className={`rounded-lg border p-3 text-sm transition-all duration-300 ${
        isHighlighted
          ? 'border-gray-900 dark:border-white/40 bg-gray-50 dark:bg-white/5'
          : 'border-gray-100 dark:border-white/10 bg-gray-50/50 dark:bg-white/[0.02]'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-xs font-semibold">
            {index + 1}
          </span>
          <span className="font-medium text-gray-800 dark:text-gray-200 truncate">
            {citation.documentName}
          </span>
          {citation.pageNumber != null && (
            <span className="flex-shrink-0 text-xs font-medium px-1.5 py-0.5 rounded bg-gray-100 dark:bg-white/10 text-gray-500 dark:text-gray-400">
              Page {citation.pageNumber}
            </span>
          )}
        </div>
        <span
          className={`flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
            scorePercent >= 70
              ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400'
              : scorePercent >= 40
                ? 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-600 dark:text-yellow-400'
                : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
          }`}
        >
          {scorePercent}%
        </span>
      </div>

      <p className="text-gray-500 dark:text-gray-400 text-xs leading-relaxed">
        {isContentExpanded ? citation.chunkContent : previewContent}
      </p>

      {citation.chunkContent.length > CONTENT_PREVIEW_LENGTH && (
        <button
          onClick={() => setIsContentExpanded(!isContentExpanded)}
          className="mt-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 font-medium"
        >
          {isContentExpanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  );
}
