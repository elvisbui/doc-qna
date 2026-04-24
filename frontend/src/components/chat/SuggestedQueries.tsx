interface SuggestedQueriesProps {
  queries: string[];
  onSelect: (query: string) => void;
}

export function SuggestedQueries({ queries, onSelect }: SuggestedQueriesProps) {
  if (queries.length === 0) return null;

  return (
    <div className="px-4 py-3" data-testid="suggested-queries">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Try</p>
      <div className="flex flex-wrap gap-2">
        {queries.map((query) => (
          <button
            key={query}
            onClick={() => onSelect(query)}
            className="inline-flex items-center rounded-full border border-gray-200 dark:border-white/15 bg-white dark:bg-white/5 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
          >
            {query}
          </button>
        ))}
      </div>
    </div>
  );
}
