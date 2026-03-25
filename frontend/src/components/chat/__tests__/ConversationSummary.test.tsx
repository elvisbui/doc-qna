import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { ConversationSummary } from '../ConversationSummary';

describe('ConversationSummary', () => {
  it('renders the summary header', () => {
    render(<ConversationSummary summary="The user asked about Python docs." />);
    expect(screen.getByText('Conversation summary')).toBeInTheDocument();
  });

  it('does not show summary text when collapsed', () => {
    render(<ConversationSummary summary="The user asked about Python docs." />);
    expect(screen.queryByText('The user asked about Python docs.')).not.toBeInTheDocument();
  });

  it('shows summary text when expanded', async () => {
    const user = userEvent.setup();
    render(<ConversationSummary summary="The user asked about Python docs." />);

    await user.click(screen.getByText('Conversation summary'));

    expect(screen.getByText('The user asked about Python docs.')).toBeInTheDocument();
  });

  it('toggles visibility on repeated clicks', async () => {
    const user = userEvent.setup();
    render(<ConversationSummary summary="Summary text here." />);

    // Expand
    await user.click(screen.getByText('Conversation summary'));
    expect(screen.getByText('Summary text here.')).toBeInTheDocument();

    // Collapse
    await user.click(screen.getByText('Conversation summary'));
    expect(screen.queryByText('Summary text here.')).not.toBeInTheDocument();
  });
});
