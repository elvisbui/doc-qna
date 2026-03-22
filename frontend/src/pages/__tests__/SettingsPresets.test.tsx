import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SettingsPage } from '../SettingsPage';

const defaultSettings = {
  llmProvider: 'ollama',
  ollamaBaseUrl: 'http://localhost:11434',
  ollamaModel: 'llama3.2',
  embeddingProvider: 'openai',
  embeddingModel: 'text-embedding-3-small',
  chunkingStrategy: 'fixed',
  retrievalStrategy: 'vector',
  chunkSize: 1000,
  chunkOverlap: 200,
  logLevel: 'INFO',
  hasOpenaiKey: true,
  hasAnthropicKey: false,
  hasCloudflareToken: false,
  openaiKeyHint: '********t-key',
  anthropicKeyHint: '',
  cloudflareKeyHint: '',
  systemPrompt: '',
  llmTemperature: 0.7,
  llmTopP: 1.0,
  llmMaxTokens: 2048,
};

const mockPresets = [
  {
    id: 'general',
    name: 'General',
    description: 'Default general-purpose RAG prompt',
    systemPrompt: 'Use the following context to answer the question.\n\nContext:\n{context}',
  },
  {
    id: 'customer_support',
    name: 'Customer Support',
    description: 'Friendly support agent',
    systemPrompt: 'You are a helpful customer support agent.\n\nContext:\n{context}',
  },
];

const mockAddToast = vi.fn();

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/settings/presets')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPresets),
        });
      }
      if (url.includes('/api/settings/ollama-models')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ models: [] }),
        });
      }
      if (url.includes('/api/settings')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...defaultSettings }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    }),
  );
});

afterEach(async () => {
  cleanup();
  await new Promise((r) => setTimeout(r, 10));
});

function renderPage(settingsOverrides: Record<string, unknown> = {}) {
  const settings = { ...defaultSettings, ...settingsOverrides };

  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/api/settings/presets')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPresets),
        });
      }
      if (url.includes('/api/settings/ollama-models')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ models: [] }),
        });
      }
      if (url.includes('/api/settings')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(settings),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    }),
  );

  render(<SettingsPage addToast={mockAddToast} />);
  return settings;
}

describe('SettingsPage - Prompt Presets', () => {
  it('renders the preset dropdown', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('preset-select')).toBeInTheDocument();
    });
  });

  it('shows preset options in the dropdown', async () => {
    renderPage();

    await waitFor(() => {
      const select = screen.getByTestId('preset-select') as HTMLSelectElement;
      const options = Array.from(select.options).map((o) => o.text);
      expect(options).toContain('General');
      expect(options).toContain('Customer Support');
      expect(options).toContain('Custom');
    });
  });

  it('selecting a preset updates the textarea', async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('preset-select')).toBeInTheDocument();
    });

    // Wait for presets to load into the dropdown
    await waitFor(() => {
      const select = screen.getByTestId('preset-select') as HTMLSelectElement;
      expect(Array.from(select.options).some((o) => o.value === 'customer_support')).toBe(true);
    });

    const select = screen.getByTestId('preset-select');
    await user.selectOptions(select, 'customer_support');

    await waitFor(() => {
      const textarea = screen.getByTestId('system-prompt-textarea') as HTMLTextAreaElement;
      expect(textarea.value).toContain('customer support agent');
    });
  });

  it('manually editing textarea switches dropdown to Custom', async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('system-prompt-textarea')).toBeInTheDocument();
    });

    const textarea = screen.getByTestId('system-prompt-textarea');
    await user.click(textarea);
    await user.type(textarea, 'My custom prompt');

    await waitFor(() => {
      const select = screen.getByTestId('preset-select') as HTMLSelectElement;
      expect(select.value).toBe('custom');
    });
  });
});
