import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { Widget } from '../Widget';

describe('Widget', () => {
  it('renders a chat button', () => {
    render(<Widget apiUrl="http://localhost:8000" />);
    expect(screen.getByTestId('widget-button')).toBeInTheDocument();
  });

  it('clicking button opens chat panel', async () => {
    const user = userEvent.setup();
    render(<Widget apiUrl="http://localhost:8000" />);

    expect(screen.queryByTestId('chat-panel')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('widget-button'));
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
  });

  it('clicking close button closes panel', async () => {
    const user = userEvent.setup();
    render(<Widget apiUrl="http://localhost:8000" />);

    await user.click(screen.getByTestId('widget-button'));
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument();

    await user.click(screen.getByTestId('close-button'));
    expect(screen.queryByTestId('chat-panel')).not.toBeInTheDocument();
  });

  it('input field and send button exist when open', async () => {
    const user = userEvent.setup();
    render(<Widget apiUrl="http://localhost:8000" />);

    await user.click(screen.getByTestId('widget-button'));
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    expect(screen.getByTestId('send-button')).toBeInTheDocument();
  });
});
