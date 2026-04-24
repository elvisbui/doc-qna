import { useState, useEffect, useRef } from 'react';
import type { Citation } from '@/types';

interface CitationPanelProps {
  citations: Citation[];
  highlightedIndex?: number | null;
}

export function CitationPanel({ citations, highlightedIndex }: CitationPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (highlightedIndex != null) {
      setIsExpanded(true);
    }
  }, [highlightedIndex]);

  if (citations.length === 0) return null;

  return (
    <div className="max-w-3xl mx-auto w-full border-t border-gray-200 dark:border-white/10">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
      >
        <span>Sources ({citations.length})</span>
        <svg
          className={`h-4 w-4 text-gray-400 dark:text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 pt-1 space-y-4 animate-fade-in">
          {citations.map((citation, index) => (
            <CitationItem key={index} citation={citation} index={index} isHighlighted={highlightedIndex === index + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface CitationItemProps {
  citation: Citation;
  index: number;
  isHighlighted?: boolean;
}

const CONTENT_PREVIEW_LENGTH = 180;

function CitationItem({ citation, index, isHighlighted }: CitationItemProps) {
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
      ? `${citation.chunkContent.slice(0, CONTENT_PREVIEW_LENGTH)}…`
      : citation.chunkContent;

  return (
    <div
      ref={cardRef}
      className={`text-sm transition-colors ${
        isHighlighted ? 'opacity-100' : 'opacity-95'
      }`}
    >
      <div className="flex items-baseline gap-2 mb-1">
        <span className="flex-shrink-0 inline-flex items-center justify-center w-4 h-4 text-xs text-gray-500 dark:text-gray-400 font-medium">
          {index + 1}
        </span>
        <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
          {citation.documentName}
        </span>
        {citation.pageNumber != null && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Page {citation.pageNumber}
          </span>
        )}
        <span className="ml-auto flex-shrink-0 text-xs text-gray-500 dark:text-gray-400 tabular-nums">
          {scorePercent}%
        </span>
      </div>

      <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed pl-6">
        {isContentExpanded ? citation.chunkContent : previewContent}
      </p>

      {citation.chunkContent.length > CONTENT_PREVIEW_LENGTH && (
        <button
          onClick={() => setIsContentExpanded(!isContentExpanded)}
          className="ml-6 mt-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
        >
          {isContentExpanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  );
}
