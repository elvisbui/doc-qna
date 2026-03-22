import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PluginsPage } from '../PluginsPage';

const mockPlugins = [
  {
    name: 'PDF Parser',
    version: '1.2.0',
    description: 'Parses PDF documents for indexing',
    enabled: true,
    configSchema: [],
  },
  {
    name: 'Web Scraper',
    version: '0.9.1',
    description: 'Scrapes web pages for content',
    enabled: false,
    configSchema: [
      {
        name: 'max_depth',
        fieldType: 'number',
        default: 3,
        label: 'Max Depth',
        description: 'Maximum crawl depth',
      },
      {
        name: 'user_agent',
        fieldType: 'string',
        default: 'bot',
        label: 'User Agent',
        description: '',
      },
      {
        name: 'follow_redirects',
        fieldType: 'boolean',
        default: true,
        label: 'Follow Redirects',
        description: '',
      },
      {
        name: 'mode',
        fieldType: 'select',
        default: 'fast',
        label: 'Mode',
        description: '',
        options: ['fast', 'thorough'],
      },
    ],
  },
  {
    name: 'Markdown Renderer',
    version: '2.0.0',
    description: 'Renders markdown content',
    enabled: true,
    configSchema: [],
  },
];

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('PluginsPage', () => {
  it('shows loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<PluginsPage />);
    expect(screen.getByText('Loading plugins...')).toBeInTheDocument();
  });

  it('fetches and displays plugins', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('PDF Parser')).toBeInTheDocument();
    });

    expect(screen.getByText('v1.2.0')).toBeInTheDocument();
    expect(screen.getByText('Parses PDF documents for indexing')).toBeInTheDocument();

    expect(screen.getByText('Web Scraper')).toBeInTheDocument();
    expect(screen.getByText('v0.9.1')).toBeInTheDocument();
    expect(screen.getByText('Scrapes web pages for content')).toBeInTheDocument();

    expect(screen.getByText('Markdown Renderer')).toBeInTheDocument();
    expect(screen.getByText('v2.0.0')).toBeInTheDocument();

    expect(mockFetch).toHaveBeenCalledWith('/api/plugins');
  });

  it('shows enabled/disabled status for each plugin', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('PDF Parser')).toBeInTheDocument();
    });

    const toggleButtons = screen.getAllByRole('button', { name: /toggle/i });
    expect(toggleButtons).toHaveLength(3);

    // All 3 toggle buttons should be present
    expect(toggleButtons).toHaveLength(3);
  });

  it('calls toggle API when toggle button is clicked', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Scraper')).toBeInTheDocument();
    });

    // Toggle the disabled plugin (Web Scraper)
    const toggledPlugin = { ...mockPlugins[1], enabled: true };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(toggledPlugin),
    });

    const toggleButtons = screen.getAllByRole('button', { name: /toggle/i });
    await user.click(toggleButtons[1]); // Web Scraper's toggle

    expect(mockFetch).toHaveBeenCalledWith('/api/plugins/Web Scraper/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: true }),
    });
  });

  it('updates UI after successful toggle', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Scraper')).toBeInTheDocument();
    });

    // Toggle Web Scraper to enabled
    const toggledPlugin = { ...mockPlugins[1], enabled: true };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(toggledPlugin),
    });

    const toggleButtons = screen.getAllByRole('button', { name: /toggle/i });
    await user.click(toggleButtons[1]);

    // After toggle, the toggle API should have been called
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/plugins/Web Scraper/toggle',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('displays error message when fetch fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load plugins/)).toBeInTheDocument();
    });
  });

  it('shows empty state when no plugins are available', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: [] }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('No plugins installed.')).toBeInTheDocument();
    });
  });

  // -- Plugin config settings tests --

  it('shows Settings button only for plugins with configSchema', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Scraper')).toBeInTheDocument();
    });

    // Only Web Scraper has configSchema
    const settingsButtons = screen.getAllByRole('button', { name: /settings for/i });
    expect(settingsButtons).toHaveLength(1);
    expect(settingsButtons[0]).toHaveAttribute('aria-label', 'Settings for Web Scraper');
  });

  it('expands config form when Settings is clicked', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Scraper')).toBeInTheDocument();
    });

    // Mock the config GET request
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          name: 'Web Scraper',
          config: { max_depth: 3, user_agent: 'bot', follow_redirects: true, mode: 'fast' },
          configSchema: mockPlugins[1].configSchema,
        }),
    });

    const settingsBtn = screen.getByRole('button', { name: /settings for web scraper/i });
    await user.click(settingsBtn);

    await waitFor(() => {
      expect(screen.getByText('Configuration')).toBeInTheDocument();
    });

    // Verify config fields are rendered
    expect(screen.getByLabelText('Max Depth')).toBeInTheDocument();
    expect(screen.getByLabelText('User Agent')).toBeInTheDocument();
    expect(screen.getByLabelText('Follow Redirects')).toBeInTheDocument();
    expect(screen.getByLabelText('Mode')).toBeInTheDocument();

    // Verify the GET config fetch was called
    expect(mockFetch).toHaveBeenCalledWith('/api/plugins/Web Scraper/config');
  });

  it('collapses config form when Settings is clicked again', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Scraper')).toBeInTheDocument();
    });

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          name: 'Web Scraper',
          config: { max_depth: 3, user_agent: 'bot', follow_redirects: true, mode: 'fast' },
          configSchema: mockPlugins[1].configSchema,
        }),
    });

    const settingsBtn = screen.getByRole('button', { name: /settings for web scraper/i });
    await user.click(settingsBtn);

    await waitFor(() => {
      expect(screen.getByText('Configuration')).toBeInTheDocument();
    });

    // Click again to collapse
    await user.click(settingsBtn);

    await waitFor(() => {
      expect(screen.queryByText('Configuration')).not.toBeInTheDocument();
    });
  });

  it('saves config when Save button is clicked', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ plugins: mockPlugins }),
    });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(screen.getByText('Web Scraper')).toBeInTheDocument();
    });

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          name: 'Web Scraper',
          config: { max_depth: 3, user_agent: 'bot', follow_redirects: true, mode: 'fast' },
          configSchema: mockPlugins[1].configSchema,
        }),
    });

    const settingsBtn = screen.getByRole('button', { name: /settings for web scraper/i });
    await user.click(settingsBtn);

    await waitFor(() => {
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    // Mock the PUT config request
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          name: 'Web Scraper',
          config: { max_depth: 3, user_agent: 'bot', follow_redirects: true, mode: 'fast' },
        }),
    });

    await user.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/plugins/Web Scraper/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config: { max_depth: 3, user_agent: 'bot', follow_redirects: true, mode: 'fast' },
        }),
      });
    });
  });
});
