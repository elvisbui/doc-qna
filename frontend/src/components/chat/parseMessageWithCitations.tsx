import { CitationLink } from './CitationLink';

/**
 * Parse a text string for citation markers matching the regex /\[(\d+)\]/g
 * and replace them with CitationLink components.
 * @param text - The raw text to scan for citation markers
 * @param onCitationClick - Callback invoked when a citation is clicked
 * @returns Array of React nodes with text segments and CitationLink components
 */
export function parseMessageWithCitations(
  text: string,
  onCitationClick: (n: number) => void,
): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = regex.exec(text)) !== null) {
    // Add text before this citation
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const citationIndex = parseInt(match[1], 10);
    parts.push(
      <CitationLink
        key={`cite-${key++}`}
        index={citationIndex}
        onClick={onCitationClick}
      />,
    );
    lastIndex = regex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}
