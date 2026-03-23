/** Props for the CitationLink component. */
interface CitationLinkProps {
  /** The 1-based citation number to display */
  index: number;
  /** Callback when the citation badge is clicked or activated via keyboard */
  onClick: (index: number) => void;
}

/** Clickable superscript citation badge rendered inline within message text. */
export function CitationLink({ index, onClick }: CitationLinkProps) {
  return (
    <sup
      role="button"
      tabIndex={0}
      aria-label={`Citation source ${index}`}
      title={`Source ${index}`}
      onClick={() => onClick(index)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick(index);
        }
      }}
      className="inline-flex items-center justify-center ml-0.5 mr-0.5 cursor-pointer select-none rounded-full bg-gray-200 dark:bg-white/15 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-white/25 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-1 transition-colors text-[10px] font-semibold leading-none px-1.5 py-0.5 align-super"
    >
      [{index}]
    </sup>
  );
}
