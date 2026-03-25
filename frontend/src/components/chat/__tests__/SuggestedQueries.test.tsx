import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SuggestedQueries } from '../SuggestedQueries';

describe('SuggestedQueries', () => {
  it('renders nothing when queries array is empty', () => {
    const { container } = render(<SuggestedQueries queries={[]} onSelect={vi.fn()} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders suggested query buttons', () => {
    const queries = ['What is Python?', 'How does async work?'];
    render(<SuggestedQueries queries={queries} onSelect={vi.fn()} />);

    expect(screen.getByText('Try asking:')).toBeInTheDocument();
    expect(screen.getByText('What is Python?')).toBeInTheDocument();
    expect(screen.getByText('How does async work?')).toBeInTheDocument();
  });

  it('calls onSelect with query text when button is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const queries = ['What is Python?', 'How does async work?'];
    render(<SuggestedQueries queries={queries} onSelect={onSelect} />);

    await user.click(screen.getByText('What is Python?'));
    expect(onSelect).toHaveBeenCalledWith('What is Python?');
  });

  it('renders each query as a button element', () => {
    const queries = ['Question 1', 'Question 2', 'Question 3'];
    render(<SuggestedQueries queries={queries} onSelect={vi.fn()} />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(3);
  });

  it('has a data-testid attribute for testing', () => {
    render(<SuggestedQueries queries={['Test?']} onSelect={vi.fn()} />);
    expect(screen.getByTestId('suggested-queries')).toBeInTheDocument();
  });
});
