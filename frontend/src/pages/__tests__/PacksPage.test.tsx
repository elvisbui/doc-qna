import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PacksPage } from '../PacksPage';

const mockPacks = [
  {
    name: 'python-docs',
    version: '1.0.0',
    description: 'Python standard library documentation',
    docCount: 42,
    installed: false,
    suggestedQueries: ['What are Python decorators?', 'How do list comprehensions work?'],
  },
  {
    name: 'react-guides',
    version: '2.1.0',
    description: 'React official guides and tutorials',
    docCount: 18,
    installed: true,
    suggestedQueries: ['What is JSX?', 'How do hooks work?'],
  },
  {
    name: 'kubernetes-ref',
    version: '0.5.0',
    description: 'Kubernetes API reference',
    docCount: 95,
    installed: false,
    suggestedQueries: [],
  },
];

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('PacksPage', () => {
  it('shows loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<PacksPage />);
    expect(screen.getByText('Loading packs...')).toBeInTheDocument();
  });

  it('fetches and displays packs', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: mockPacks }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('python-docs')).toBeInTheDocument();
    });

    expect(screen.getByText('v1.0.0')).toBeInTheDocument();
    expect(screen.getByText('Python standard library documentation')).toBeInTheDocument();
    expect(screen.getByText('42 documents')).toBeInTheDocument();

    expect(screen.getByText('react-guides')).toBeInTheDocument();
    expect(screen.getByText('v2.1.0')).toBeInTheDocument();
    expect(screen.getByText('React official guides and tutorials')).toBeInTheDocument();
    expect(screen.getByText('18 documents')).toBeInTheDocument();

    expect(screen.getByText('kubernetes-ref')).toBeInTheDocument();
    expect(screen.getByText('v0.5.0')).toBeInTheDocument();
    expect(screen.getByText('95 documents')).toBeInTheDocument();

    expect(mockFetch).toHaveBeenCalledWith('/api/packs');
  });

  it('shows Install button for uninstalled packs and Uninstall for installed', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: mockPacks }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('python-docs')).toBeInTheDocument();
    });

    const installButtons = screen.getAllByRole('button', { name: /^Install$/i });
    expect(installButtons).toHaveLength(2); // two uninstalled packs

    const uninstallButtons = screen.getAllByRole('button', { name: /Uninstall/i });
    expect(uninstallButtons).toHaveLength(1); // one installed pack
  });

  it('calls install API when Install button is clicked', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: mockPacks }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('python-docs')).toBeInTheDocument();
    });

    const installedPack = {
      name: 'python-docs',
      version: '1.0.0',
      description: 'Python standard library documentation',
      docCount: 42,
      installed: true,
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(installedPack),
    });

    const installButtons = screen.getAllByRole('button', { name: /^Install$/i });
    await user.click(installButtons[0]); // python-docs Install button

    expect(mockFetch).toHaveBeenCalledWith('/api/packs/python-docs/install', {
      method: 'POST',
    });
  });

  it('updates UI after successful install', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: mockPacks }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('python-docs')).toBeInTheDocument();
    });

    // Initially 2 install buttons
    expect(screen.getAllByRole('button', { name: /^Install$/i })).toHaveLength(2);

    const installedPack = {
      name: 'python-docs',
      version: '1.0.0',
      description: 'Python standard library documentation',
      docCount: 42,
      installed: true,
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(installedPack),
    });

    const installButtons = screen.getAllByRole('button', { name: /^Install$/i });
    await user.click(installButtons[0]);

    await waitFor(() => {
      // After install, only 1 install button left
      expect(screen.getAllByRole('button', { name: /^Install$/i })).toHaveLength(1);
    });

    // Now should have 2 uninstall buttons
    expect(screen.getAllByRole('button', { name: /Uninstall/i })).toHaveLength(2);
  });

  it('calls uninstall API when Uninstall button is clicked', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: mockPacks }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('react-guides')).toBeInTheDocument();
    });

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ name: 'react-guides', uninstalled: true }),
    });

    const uninstallButton = screen.getByRole('button', { name: /Uninstall/i });
    await user.click(uninstallButton);

    expect(mockFetch).toHaveBeenCalledWith('/api/packs/react-guides/uninstall', {
      method: 'POST',
    });
  });

  it('updates UI after successful uninstall', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: mockPacks }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('react-guides')).toBeInTheDocument();
    });

    // Initially 1 uninstall button
    expect(screen.getAllByRole('button', { name: /Uninstall/i })).toHaveLength(1);

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ name: 'react-guides', uninstalled: true }),
    });

    const uninstallButton = screen.getByRole('button', { name: /Uninstall/i });
    await user.click(uninstallButton);

    await waitFor(() => {
      // After uninstall, 3 install buttons (all uninstalled)
      expect(screen.getAllByRole('button', { name: /^Install$/i })).toHaveLength(3);
    });
  });

  it('displays error message when fetch fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error'),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load packs/)).toBeInTheDocument();
    });
  });

  it('shows empty state when no packs are available', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: [] }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('No knowledge packs available.')).toBeInTheDocument();
    });
  });

  it('shows installing state while install is in progress', async () => {
    const user = userEvent.setup();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ packs: mockPacks }),
    });

    render(<PacksPage />);

    await waitFor(() => {
      expect(screen.getByText('python-docs')).toBeInTheDocument();
    });

    // Make install never resolve to see the installing state
    mockFetch.mockReturnValueOnce(new Promise(() => {}));

    const installButtons = screen.getAllByRole('button', { name: /^Install$/i });
    await user.click(installButtons[0]);

    expect(screen.getByText('Installing...')).toBeInTheDocument();
  });
});
