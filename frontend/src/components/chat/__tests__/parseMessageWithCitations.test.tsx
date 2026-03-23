import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { parseMessageWithCitations } from '../parseMessageWithCitations';

describe('parseMessageWithCitations', () => {
  const noop = vi.fn();

  it('returns single text node for plain text without citations', () => {
    const result = parseMessageWithCitations('Hello world', noop);
    expect(result).toHaveLength(1);
    expect(result[0]).toBe('Hello world');
  });

  it('parses text with [1] into text + CitationLink + text', () => {
    const result = parseMessageWithCitations(
      'This is a fact [1] and more text.',
      noop,
    );
    // Should be: "This is a fact ", <CitationLink index={1} />, " and more text."
    expect(result).toHaveLength(3);
    expect(result[0]).toBe('This is a fact ');
    expect(result[2]).toBe(' and more text.');

    // Render the middle element to verify it's a CitationLink
    const { container } = render(<>{result[1]}</>);
    expect(container.textContent).toBe('[1]');
  });

  it('parses multiple citations [1] and [2]', () => {
    const result = parseMessageWithCitations(
      'First [1] second [2] end.',
      noop,
    );
    expect(result).toHaveLength(5);
    expect(result[0]).toBe('First ');
    expect(result[2]).toBe(' second ');
    expect(result[4]).toBe(' end.');

    const { container } = render(
      <>
        {result[1]}
        {result[3]}
      </>,
    );
    expect(container.textContent).toBe('[1][2]');
  });

  it('handles citation at start of text', () => {
    const result = parseMessageWithCitations('[1] starts here', noop);
    expect(result).toHaveLength(2);
    expect(result[1]).toBe(' starts here');

    const { container } = render(<>{result[0]}</>);
    expect(container.textContent).toBe('[1]');
  });

  it('handles citation at end of text', () => {
    const result = parseMessageWithCitations('ends here [3]', noop);
    expect(result).toHaveLength(2);
    expect(result[0]).toBe('ends here ');

    const { container } = render(<>{result[1]}</>);
    expect(container.textContent).toBe('[3]');
  });

  it('returns empty array for empty string', () => {
    const result = parseMessageWithCitations('', noop);
    expect(result).toHaveLength(0);
  });
});
