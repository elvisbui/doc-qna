import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { LandingPage } from '../LandingPage';

describe('LandingPage', () => {
  it('renders heading and input', () => {
    render(<LandingPage onNavigateToChat={() => {}} />);
    expect(screen.getByText('Ask Your Documents Anything')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ask anything')).toBeInTheDocument();
  });

  it('renders attach file button', () => {
    render(<LandingPage onNavigateToChat={() => {}} />);
    expect(screen.getByTitle('Upload a document')).toBeInTheDocument();
  });

  it('submits query on Enter and navigates to chat', async () => {
    const user = userEvent.setup();
    const onNavigateToChat = vi.fn();

    render(<LandingPage onNavigateToChat={onNavigateToChat} />);

    const textarea = screen.getByPlaceholderText('Ask anything');
    await user.type(textarea, 'What is Python?');
    await user.keyboard('{Enter}');

    expect(onNavigateToChat).toHaveBeenCalledWith('What is Python?');
  });

  it('does not submit empty query', async () => {
    const user = userEvent.setup();
    const onNavigateToChat = vi.fn();

    render(<LandingPage onNavigateToChat={onNavigateToChat} />);

    const textarea = screen.getByPlaceholderText('Ask anything');
    await user.click(textarea);
    await user.keyboard('{Enter}');

    expect(onNavigateToChat).not.toHaveBeenCalled();
  });

  it('sends query via send button click', async () => {
    const user = userEvent.setup();
    const onNavigateToChat = vi.fn();

    render(<LandingPage onNavigateToChat={onNavigateToChat} />);

    const textarea = screen.getByPlaceholderText('Ask anything');
    await user.type(textarea, 'Hello world');

    // Send button is the round black button
    const buttons = screen.getAllByRole('button');
    const sendButton = buttons.find(
      (b) => !b.hasAttribute('disabled') && b !== screen.getByTitle('Upload a document'),
    );
    if (sendButton) await user.click(sendButton);

    expect(onNavigateToChat).toHaveBeenCalledWith('Hello world');
  });
});
