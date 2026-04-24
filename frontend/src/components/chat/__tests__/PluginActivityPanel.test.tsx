import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { PluginActivityPanel } from '../PluginActivityPanel';
import type { PluginTraceEntry } from '@/types';

describe('PluginActivityPanel', () => {
  it('renders nothing when trace is empty', () => {
    const { container } = render(<PluginActivityPanel trace={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows plugin activity header with count', () => {
    const trace: PluginTraceEntry[] = [
      { pluginName: 'summarizer', hookName: 'on_post_generate', durationMs: 12.5, error: false },
    ];
    render(<PluginActivityPanel trace={trace} />);
    expect(screen.getByText(/Plugin activity/)).toBeInTheDocument();
    expect(screen.getByText(/1/)).toBeInTheDocument();
  });

  it('expands to show plugin details when clicked', async () => {
    const user = userEvent.setup();
    const trace: PluginTraceEntry[] = [
      { pluginName: 'summarizer', hookName: 'on_post_generate', durationMs: 12.5, error: false },
      { pluginName: 'reranker', hookName: 'on_post_retrieve', durationMs: 5.3, error: false },
    ];
    render(<PluginActivityPanel trace={trace} />);

    // Click the header to expand
    const button = screen.getByRole('button');
    await user.click(button);

    expect(screen.getByText('summarizer')).toBeInTheDocument();
    expect(screen.getByText('reranker')).toBeInTheDocument();
    expect(screen.getByText(/12\.5\s*ms/)).toBeInTheDocument();
    expect(screen.getByText(/5\.3\s*ms/)).toBeInTheDocument();
  });

  it('shows error indicator for failed plugins', async () => {
    const user = userEvent.setup();
    const trace: PluginTraceEntry[] = [
      { pluginName: 'broken_plugin', hookName: 'on_post_generate', durationMs: 1.0, error: true },
    ];
    render(<PluginActivityPanel trace={trace} />);

    const button = screen.getByRole('button');
    await user.click(button);

    expect(screen.getByText('broken_plugin')).toBeInTheDocument();
    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });

  it('shows hook name for each entry', async () => {
    const user = userEvent.setup();
    const trace: PluginTraceEntry[] = [
      { pluginName: 'test_plugin', hookName: 'on_post_generate', durationMs: 3.0, error: false },
    ];
    render(<PluginActivityPanel trace={trace} />);

    const button = screen.getByRole('button');
    await user.click(button);

    expect(screen.getByText(/on_post_generate/)).toBeInTheDocument();
  });
});
