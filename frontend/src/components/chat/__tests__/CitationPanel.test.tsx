import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { CitationPanel } from '../CitationPanel';
import type { Citation } from '@/types';

function makeCitation(overrides: Partial<Citation> = {}): Citation {
  return {
    documentId: 'doc-1',
    documentName: 'report.pdf',
    chunkContent: 'Some relevant content from the document.',
    chunkIndex: 0,
    relevanceScore: 0.85,
    ...overrides,
  };
}

describe('CitationPanel', () => {
  it('renders nothing when citations are empty', () => {
    const { container } = render(<CitationPanel citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders sources count', () => {
    render(<CitationPanel citations={[makeCitation()]} />);
    expect(screen.getByText('Sources (1)')).toBeInTheDocument();
  });

  it('renders citation without page number', async () => {
    const user = userEvent.setup();
    render(
      <CitationPanel citations={[makeCitation({ pageNumber: undefined })]} />,
    );

    // Expand the panel
    await user.click(screen.getByText('Sources (1)'));

    expect(screen.getByText('report.pdf')).toBeInTheDocument();
    expect(screen.queryByText(/Page /)).not.toBeInTheDocument();
  });

  it('renders citation with page number showing "Page X"', async () => {
    const user = userEvent.setup();
    render(
      <CitationPanel citations={[makeCitation({ pageNumber: 5 })]} />,
    );

    // Expand the panel
    await user.click(screen.getByText('Sources (1)'));

    expect(screen.getByText('report.pdf')).toBeInTheDocument();
    expect(screen.getByText('Page 5')).toBeInTheDocument();
  });

  it('renders multiple citations with mixed page numbers', async () => {
    const user = userEvent.setup();
    const citations = [
      makeCitation({ documentName: 'doc1.pdf', pageNumber: 3 }),
      makeCitation({ documentName: 'notes.md', pageNumber: undefined }),
      makeCitation({ documentName: 'doc2.pdf', pageNumber: 12 }),
    ];
    render(<CitationPanel citations={citations} />);

    await user.click(screen.getByText('Sources (3)'));

    expect(screen.getByText('Page 3')).toBeInTheDocument();
    expect(screen.getByText('Page 12')).toBeInTheDocument();
    // notes.md should not have a page badge
    expect(screen.queryAllByText(/Page /).length).toBe(2);
  });
});
