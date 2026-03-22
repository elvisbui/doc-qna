import { render, screen, waitFor, within, cleanup } from '@testing-library/react';
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

const mockAddToast = vi.fn();

/**
 * Helper: create a URL-based fetch mock that routes requests correctly.
 * Supports optional overrides for specific URLs and records all calls
 * so tests can inspect POST/PUT requests.
 */
function createFetchMock(
  settingsData: Record<string, unknown> = defaultSettings,
  ollamaModelsData: { models: unknown[]; error?: string } = { models: [] },
) {
  const calls: [string, RequestInit | undefined][] = [];

  const mock = vi.fn((url: string, init?: RequestInit) => {
    calls.push([url, init]);

    if (typeof url === 'string' && url.includes('/api/settings/presets')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      });
    }
    if (typeof url === 'string' && url.includes('/api/settings/ollama-models')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(ollamaModelsData),
      });
    }
    if (typeof url === 'string' && url.includes('/api/settings/api-keys')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(settingsData),
      });
    }
    if (typeof url === 'string' && url.includes('/api/settings')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(settingsData),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({}),
    });
  });

  return { mock, calls };
}

beforeEach(() => {
  const { mock } = createFetchMock();
  vi.stubGlobal('fetch', mock);
});

afterEach(async () => {
  cleanup();
  // Flush pending microtasks so async effects from the previous render settle
  await new Promise((r) => setTimeout(r, 10));
});

function renderWithSettings(
  settingsOverrides: Record<string, unknown> = {},
  ollamaModelsData: { models: unknown[]; error?: string } = { models: [] },
) {
  const settings = { ...defaultSettings, ...settingsOverrides };
  const { mock } = createFetchMock(settings, ollamaModelsData);
  vi.stubGlobal('fetch', mock);
  render(<SettingsPage addToast={mockAddToast} />);
  return { settings, mock };
}

describe('SettingsPage - Embedding Model Picker', () => {
  it('renders the Embedding Configuration section', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('Embedding Configuration')).toBeInTheDocument();
    });
  });

  it('shows Embedding Provider dropdown', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('Embedding Provider')).toBeInTheDocument();
    });
  });

  it('shows Embedding Model label', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('Embedding Model')).toBeInTheDocument();
    });
  });

  it('displays OpenAI embedding models when provider is openai', async () => {
    renderWithSettings({
      llmProvider: 'openai',
      embeddingProvider: 'openai',
    });

    await waitFor(() => {
      const embeddingSection = screen.getByText('Embedding Configuration').closest('section')!;
      const selects = within(embeddingSection).getAllByRole('combobox');
      expect(selects.length).toBeGreaterThanOrEqual(2);
      const modelSelect = selects[1];
      const options = within(modelSelect).getAllByRole('option');
      const optionValues = options.map((o) => (o as HTMLOptionElement).value);

      expect(optionValues).toContain('text-embedding-3-small');
      expect(optionValues).toContain('text-embedding-3-large');
      expect(optionValues).toContain('text-embedding-ada-002');
    });
  });

  it('selects the current OpenAI embedding model', async () => {
    renderWithSettings({
      llmProvider: 'openai',
      embeddingProvider: 'openai',
      embeddingModel: 'text-embedding-3-large',
    });

    await waitFor(() => {
      const embeddingSection = screen.getByText('Embedding Configuration').closest('section')!;
      const selects = within(embeddingSection).getAllByRole('combobox');
      expect(selects.length).toBeGreaterThanOrEqual(2);
      const modelSelect = selects[1] as HTMLSelectElement;
      expect(modelSelect.value).toBe('text-embedding-3-large');
    });
  });

  it('shows Ollama fallback models when provider is ollama and fetch fails', async () => {
    renderWithSettings(
      {
        embeddingProvider: 'ollama',
        embeddingModel: 'nomic-embed-text',
      },
      { models: [], error: 'Could not connect' },
    );

    await waitFor(() => {
      expect(screen.getByText('Embedding Configuration')).toBeInTheDocument();
    });

    const embeddingSection = screen.getByText('Embedding Configuration').closest('section')!;

    // Should show fallback models
    await waitFor(() => {
      const selects = within(embeddingSection).getAllByRole('combobox');
      // The embedding model select should contain fallback Ollama models
      const modelSelect = selects[1];
      const options = within(modelSelect).getAllByRole('option');
      const optionValues = options.map((o) => (o as HTMLOptionElement).value);

      expect(optionValues).toContain('nomic-embed-text');
      expect(optionValues).toContain('mxbai-embed-large');
      expect(optionValues).toContain('all-minilm');
    });
  });

  it('shows fetched Ollama models when provider is ollama and fetch succeeds', async () => {
    const ollamaModels = [
      { name: 'nomic-embed-text', size: '274.0 MB', modified: '2025-01-15' },
      { name: 'mxbai-embed-large', size: '669.0 MB', modified: '2025-01-14' },
    ];

    renderWithSettings(
      {
        embeddingProvider: 'ollama',
        embeddingModel: 'nomic-embed-text',
      },
      { models: ollamaModels },
    );

    await waitFor(() => {
      expect(screen.getByText('Embedding Configuration')).toBeInTheDocument();
    });

    const embeddingSection = screen.getByText('Embedding Configuration').closest('section')!;

    await waitFor(() => {
      const selects = within(embeddingSection).getAllByRole('combobox');
      const modelSelect = selects[1];
      const options = within(modelSelect).getAllByRole('option');
      const optionValues = options.map((o) => (o as HTMLOptionElement).value);
      expect(optionValues).toContain('nomic-embed-text');
      expect(optionValues).toContain('mxbai-embed-large');
    });
  });

  it('shows Refresh button for Ollama embedding models', async () => {
    renderWithSettings({
      embeddingProvider: 'ollama',
      embeddingModel: 'nomic-embed-text',
    });

    await waitFor(() => {
      const embeddingSection = screen.getByText('Embedding Configuration').closest('section')!;
      const refreshButton = within(embeddingSection).queryByText('Refresh');
      expect(refreshButton).toBeInTheDocument();
    });
  });

  it('changes embedding model when user selects a different OpenAI model', async () => {
    const user = userEvent.setup();
    renderWithSettings({
      llmProvider: 'openai',
      embeddingProvider: 'openai',
      embeddingModel: 'text-embedding-3-small',
    });

    // Wait for the embedding model select to appear (openai branch renders a raw <select>)
    let modelSelect: HTMLSelectElement;
    await waitFor(() => {
      const label = screen.getByText('Embedding Model');
      const select = label.parentElement!.querySelector('select');
      expect(select).not.toBeNull();
      modelSelect = select as HTMLSelectElement;
    });

    await user.selectOptions(modelSelect!, 'text-embedding-3-large');
    expect(modelSelect!.value).toBe('text-embedding-3-large');
  });

  it('switches embedding provider from openai to ollama', async () => {
    const user = userEvent.setup();
    renderWithSettings({
      embeddingProvider: 'openai',
      embeddingModel: 'text-embedding-3-small',
    });

    await waitFor(() => {
      expect(screen.getByText('Embedding Configuration')).toBeInTheDocument();
    });

    const embeddingSection = screen.getByText('Embedding Configuration').closest('section')!;
    const selects = within(embeddingSection).getAllByRole('combobox');
    const providerSelect = selects[0] as HTMLSelectElement;

    expect(providerSelect.value).toBe('openai');

    await user.selectOptions(providerSelect, 'ollama');
    expect(providerSelect.value).toBe('ollama');
  });

  it('sends updated embedding model when saving settings', async () => {
    const user = userEvent.setup();
    const { mock } = renderWithSettings({
      llmProvider: 'openai',
      embeddingProvider: 'openai',
      embeddingModel: 'text-embedding-3-small',
    });

    await waitFor(() => {
      expect(screen.getByText('Embedding Configuration')).toBeInTheDocument();
    });

    // Change embedding model
    const embeddingSection = screen.getByText('Embedding Configuration').closest('section')!;
    let modelSelect!: HTMLSelectElement;
    await waitFor(() => {
      const selects = within(embeddingSection).getAllByRole('combobox');
      expect(selects.length).toBeGreaterThanOrEqual(2);
      modelSelect = selects[1] as HTMLSelectElement;
    });
    await user.selectOptions(modelSelect, 'text-embedding-ada-002');

    // Click Save Settings
    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    await user.click(saveButton);

    // Verify the PUT call included the new embedding model
    await waitFor(() => {
      const putCall = mock.mock.calls.find(
        (call: unknown[]) => call[1] && (call[1] as RequestInit).method === 'PUT',
      );
      expect(putCall).toBeDefined();
      const body = JSON.parse((putCall![1] as RequestInit).body as string);
      expect(body.embeddingModel).toBe('text-embedding-ada-002');
    });
  });
});

describe('SettingsPage - Model Parameters', () => {
  it('renders the Model Parameters section', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('Model Parameters')).toBeInTheDocument();
    });
  });

  it('renders Temperature input with default value', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = document.getElementById('field-temperature')!;
      expect(input).toBeInTheDocument();
      expect(input).toHaveValue(0.7);
    });
  });

  it('renders Top P input with default value', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = document.getElementById('field-top-p')!;
      expect(input).toBeInTheDocument();
      expect(input).toHaveValue(1.0);
    });
  });

  it('renders Max Tokens input with default value', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = document.getElementById('field-max-tokens')!;
      expect(input).toBeInTheDocument();
      expect(input).toHaveValue(2048);
    });
  });

  it('reflects custom model parameter values', async () => {
    renderWithSettings({
      llmTemperature: 0.3,
      llmTopP: 0.9,
      llmMaxTokens: 4096,
    });

    await waitFor(() => {
      expect(document.getElementById('field-temperature')!).toHaveValue(0.3);
      expect(document.getElementById('field-top-p')!).toHaveValue(0.9);
      expect(document.getElementById('field-max-tokens')!).toHaveValue(4096);
    });
  });

  it('sends model params when saving settings', async () => {
    const user = userEvent.setup();
    const { mock } = renderWithSettings();

    await waitFor(() => {
      expect(document.getElementById('field-temperature')!).toBeInTheDocument();
    });

    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    await user.click(saveButton);

    await waitFor(() => {
      const putCall = mock.mock.calls.find(
        (call: unknown[]) => call[1] && (call[1] as RequestInit).method === 'PUT',
      );
      expect(putCall).toBeDefined();
      const body = JSON.parse((putCall![1] as RequestInit).body as string);
      expect(body.llmTemperature).toBe(0.7);
      expect(body.llmTopP).toBe(1.0);
      expect(body.llmMaxTokens).toBe(2048);
    });
  });

  it('Temperature input has correct min/max attributes', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = document.getElementById('field-temperature')! as HTMLInputElement;
      expect(input.min).toBe('0');
      expect(input.max).toBe('2');
    });
  });

  it('Top P input has correct min/max attributes', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = document.getElementById('field-top-p')! as HTMLInputElement;
      expect(input.min).toBe('0');
      expect(input.max).toBe('1');
    });
  });

  it('Max Tokens input has correct min/max attributes', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = document.getElementById('field-max-tokens')! as HTMLInputElement;
      expect(input.min).toBe('128');
      expect(input.max).toBe('8192');
    });
  });
});

describe('SettingsPage - API Key Input Fields', () => {
  it('renders the API Keys section', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('API Keys')).toBeInTheDocument();
    });
  });

  it('renders password-type input for OpenAI API key', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = screen.getByTestId('openai-key-input');
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('type', 'password');
    });
  });

  it('renders password-type input for Anthropic API key', async () => {
    renderWithSettings();

    await waitFor(() => {
      const input = screen.getByTestId('anthropic-key-input');
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('type', 'password');
    });
  });

  it('shows masked key hint in placeholder when OpenAI key is configured', async () => {
    renderWithSettings({
      hasOpenaiKey: true,
      openaiKeyHint: '********ABCD',
    });

    await waitFor(() => {
      const input = screen.getByTestId('openai-key-input');
      expect(input).toHaveAttribute('placeholder', 'Current: ********ABCD');
    });
  });

  it('shows masked key hint in placeholder when Anthropic key is configured', async () => {
    renderWithSettings({
      hasAnthropicKey: true,
      anthropicKeyHint: '**********5678',
    });

    await waitFor(() => {
      const input = screen.getByTestId('anthropic-key-input');
      expect(input).toHaveAttribute('placeholder', 'Current: **********5678');
    });
  });

  it('shows default placeholder when no key is configured', async () => {
    renderWithSettings({
      hasOpenaiKey: false,
      openaiKeyHint: '',
      hasAnthropicKey: false,
      anthropicKeyHint: '',
    });

    await waitFor(() => {
      const openaiInput = screen.getByTestId('openai-key-input');
      expect(openaiInput).toHaveAttribute('placeholder', 'sk-...');
      const anthropicInput = screen.getByTestId('anthropic-key-input');
      expect(anthropicInput).toHaveAttribute('placeholder', 'sk-ant-...');
    });
  });

  it('renders the Save Keys button', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Save Keys/i })).toBeInTheDocument();
    });
  });

  it('disables Save Keys button when inputs are empty', async () => {
    renderWithSettings();

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /Save Keys/i });
      expect(btn).toBeDisabled();
    });
  });

  it('enables Save Keys button when a key is entered', async () => {
    const user = userEvent.setup();
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByTestId('openai-key-input')).toBeInTheDocument();
    });

    const input = screen.getByTestId('openai-key-input');
    await user.type(input, 'sk-new-test-key');

    const btn = screen.getByRole('button', { name: /Save Keys/i });
    expect(btn).not.toBeDisabled();
  });

  it('calls saveApiKeys POST endpoint when Save Keys is clicked', async () => {
    const user = userEvent.setup();
    const { mock } = renderWithSettings();

    await waitFor(() => {
      expect(screen.getByTestId('openai-key-input')).toBeInTheDocument();
    });

    const input = screen.getByTestId('openai-key-input');
    await user.type(input, 'sk-new-key-value');

    const btn = screen.getByRole('button', { name: /Save Keys/i });
    await user.click(btn);

    await waitFor(() => {
      const postCall = mock.mock.calls.find(
        (call: unknown[]) => {
          const opts = call[1] as RequestInit | undefined;
          return opts?.method === 'POST' && (call[0] as string).includes('api-keys');
        },
      );
      expect(postCall).toBeDefined();
      const body = JSON.parse((postCall![1] as RequestInit).body as string);
      expect(body.openaiApiKey).toBe('sk-new-key-value');
    });
  });

  it('shows "Configured" status when key is present', async () => {
    renderWithSettings({
      hasOpenaiKey: true,
      openaiKeyHint: '********test',
      hasAnthropicKey: false,
      anthropicKeyHint: '',
    });

    await waitFor(() => {
      expect(screen.getByText('API Keys')).toBeInTheDocument();
    });

    const apiKeysSection = screen.getByText('API Keys').closest('section')!;
    expect(within(apiKeysSection).getByText('Configured')).toBeInTheDocument();
    const notConfigured = within(apiKeysSection).getAllByText('Not configured');
    expect(notConfigured.length).toBeGreaterThanOrEqual(1);
  });
});

describe('SettingsPage - System Prompt', () => {
  it('renders the System Prompt section', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('System Prompt')).toBeInTheDocument();
    });
  });

  it('renders a textarea for the system prompt', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('Custom System Prompt')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Use the following context/);
    expect(textarea).toBeInTheDocument();
    expect(textarea.tagName).toBe('TEXTAREA');
  });

  it('shows the current system prompt value', async () => {
    renderWithSettings({ systemPrompt: 'You are a legal assistant.' });

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/Use the following context/);
      expect(textarea).toHaveValue('You are a legal assistant.');
    });
  });

  it('allows typing a custom system prompt', async () => {
    const user = userEvent.setup();
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('System Prompt')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Use the following context/);
    await user.click(textarea);
    await user.type(textarea, 'Be concise.');

    expect(textarea).toHaveValue('Be concise.');
  });

  it('has a Reset to default button', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('Reset to default')).toBeInTheDocument();
    });
  });

  it('includes the system prompt when saving settings', async () => {
    const user = userEvent.setup();
    const { mock } = renderWithSettings({ systemPrompt: 'Custom prompt' });

    await waitFor(() => {
      expect(screen.getByText('System Prompt')).toBeInTheDocument();
    });

    const saveButton = screen.getByRole('button', { name: /Save Settings/i });
    await user.click(saveButton);

    await waitFor(() => {
      const putCall = mock.mock.calls.find(
        (call: unknown[]) => call[1] && (call[1] as RequestInit).method === 'PUT',
      );
      expect(putCall).toBeDefined();
      const body = JSON.parse((putCall![1] as RequestInit).body as string);
      expect(body.systemPrompt).toBe('Custom prompt');
    });
  });

  it('displays helper text about {context} placeholder', async () => {
    renderWithSettings();

    await waitFor(() => {
      expect(screen.getByText('{context}')).toBeInTheDocument();
    });
  });
});
