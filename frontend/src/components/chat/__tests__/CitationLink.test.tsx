import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { CitationLink } from '../CitationLink';

describe('CitationLink', () => {
  it('renders with the correct index', () => {
    render(<CitationLink index={1} onClick={() => {}} />);
    expect(screen.getByText('[1]')).toBeInTheDocument();
  });

  it('renders with a different index', () => {
    render(<CitationLink index={3} onClick={() => {}} />);
    expect(screen.getByText('[3]')).toBeInTheDocument();
  });

  it('has a tooltip with "Source N"', () => {
    render(<CitationLink index={2} onClick={() => {}} />);
    const el = screen.getByTitle('Source 2');
    expect(el).toBeInTheDocument();
  });

  it('calls onClick with the correct index when clicked', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<CitationLink index={5} onClick={handleClick} />);

    await user.click(screen.getByText('[5]'));

    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(5);
  });

  it('calls onClick when Enter key is pressed', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<CitationLink index={2} onClick={handleClick} />);

    const el = screen.getByRole('button', { name: 'Citation source 2' });
    el.focus();
    await user.keyboard('{Enter}');

    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(2);
  });

  it('calls onClick when Space key is pressed', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<CitationLink index={4} onClick={handleClick} />);

    const el = screen.getByRole('button', { name: 'Citation source 4' });
    el.focus();
    await user.keyboard(' ');

    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(4);
  });

  it('has aria-label for screen readers', () => {
    render(<CitationLink index={3} onClick={() => {}} />);
    expect(screen.getByRole('button', { name: 'Citation source 3' })).toBeInTheDocument();
  });
});
