import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { LandingPage } from '../LandingPage';

describe('LandingPage', () => {
  it('renders heading and input', () => {
    render(<LandingPage onNavigateToChat={() => {}} />);
    expect(screen.getByText('doc-qna')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Message')).toBeInTheDocument();
  });

  it('renders attach file button', () => {
    render(<LandingPage onNavigateToChat={() => {}} />);
    expect(screen.getByTitle('Upload a document')).toBeInTheDocument();
  });

  it('submits query on Enter and navigates to chat', async () => {
    const user = userEvent.setup();
    const onNavigateToChat = vi.fn();

    render(<LandingPage onNavigateToChat={onNavigateToChat} />);

    const textarea = screen.getByPlaceholderText('Message');
    await user.type(textarea, 'What is Python?');
    await user.keyboard('{Enter}');

    expect(onNavigateToChat).toHaveBeenCalledWith('What is Python?');
  });

  it('does not submit empty query', async () => {
    const user = userEvent.setup();
    const onNavigateToChat = vi.fn();

    render(<LandingPage onNavigateToChat={onNavigateToChat} />);

    const textarea = screen.getByPlaceholderText('Message');
    await user.click(textarea);
    await user.keyboard('{Enter}');

    expect(onNavigateToChat).not.toHaveBeenCalled();
  });

  it('sends query via send button click', async () => {
    const user = userEvent.setup();
    const onNavigateToChat = vi.fn();

    render(<LandingPage onNavigateToChat={onNavigateToChat} />);

    const textarea = screen.getByPlaceholderText('Message');
    await user.type(textarea, 'Hello world');

    const sendButton = screen.getByLabelText('Send');
    await user.click(sendButton);

    expect(onNavigateToChat).toHaveBeenCalledWith('Hello world');
  });
});
