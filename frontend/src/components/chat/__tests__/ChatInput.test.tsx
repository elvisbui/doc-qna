import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ChatInput } from '../ChatInput';

describe('ChatInput', () => {
  it('renders textarea and send button', () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    expect(
      screen.getByPlaceholderText('Ask anything'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send message' })).toBeInTheDocument();
  });

  it('accepts text input', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(
      'Ask anything',
    );
    await user.type(textarea, 'Hello world');

    expect(textarea).toHaveValue('Hello world');
  });

  it('calls onSend and clears input on Enter', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(
      'Ask anything',
    );
    await user.type(textarea, 'test message{Enter}');

    expect(onSend).toHaveBeenCalledWith('test message');
    expect(textarea).toHaveValue('');
  });

  it('does not send on Shift+Enter (allows newline)', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(
      'Ask anything',
    );
    await user.type(textarea, 'line one{Shift>}{Enter}{/Shift}line two');

    expect(onSend).not.toHaveBeenCalled();
    expect(textarea).toHaveValue('line one\nline two');
  });

  it('disables textarea and button when isLoading is true', () => {
    render(<ChatInput onSend={vi.fn()} isLoading={true} />);

    const textarea = screen.getByPlaceholderText(
      'Ask anything',
    );
    const button = screen.getByRole('button', { name: 'Send message' });

    expect(textarea).toBeDisabled();
    expect(button).toBeDisabled();
  });

  it('disables send button when input is empty', () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} />);

    const button = screen.getByRole('button', { name: 'Send message' });
    expect(button).toBeDisabled();
  });

  it('does not call onSend when input is whitespace only', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(
      'Ask anything',
    );
    await user.type(textarea, '   {Enter}');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('calls onSend when send button is clicked', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} isLoading={false} />);

    const textarea = screen.getByPlaceholderText(
      'Ask anything',
    );
    await user.type(textarea, 'click test');

    const button = screen.getByRole('button', { name: 'Send message' });
    await user.click(button);

    expect(onSend).toHaveBeenCalledWith('click test');
    expect(textarea).toHaveValue('');
  });
});
