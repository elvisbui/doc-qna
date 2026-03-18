/** Props for the SuggestedQueries component. */
interface SuggestedQueriesProps {
  /** List of suggested query strings to display as clickable chips */
  queries: string[];
  /** Callback invoked when the user clicks a suggested query */
  onSelect: (query: string) => void;
}

/** Row of clickable pill buttons showing suggested queries from a knowledge pack. */
export function SuggestedQueries({ queries, onSelect }: SuggestedQueriesProps) {
  if (queries.length === 0) return null;

  return (
    <div className="px-4 py-3" data-testid="suggested-queries">
      <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
        Try asking:
      </p>
      <div className="flex flex-wrap gap-2">
        {queries.map((query) => (
          <button
            key={query}
            onClick={() => onSelect(query)}
            className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50 transition-colors"
          >
            {query}
          </button>
        ))}
      </div>
    </div>
  );
}
