import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MetricsPage } from '../MetricsPage';

const mockSummary = {
  totalQueries: 42,
  avgLatencyMs: 250.5,
  p50LatencyMs: 200.0,
  p95LatencyMs: 800.0,
  avgRelevanceScore: 0.823,
  errorRate: 0.048,
  queriesPerDay: [
    { date: '2026-03-10', count: 5 },
    { date: '2026-03-11', count: 8 },
    { date: '2026-03-12', count: 12 },
  ],
};

const mockRecent = [
  {
    id: 3,
    timestamp: 1710460800,
    queryText: 'What is RAG?',
    latencyMs: 200,
    avgRelevanceScore: 0.85,
    numChunksRetrieved: 3,
    tokenCount: null,
    error: false,
    errorMessage: null,
  },
  {
    id: 2,
    timestamp: 1710374400,
    queryText: 'Explain embeddings',
    latencyMs: 350,
    avgRelevanceScore: 0.72,
    numChunksRetrieved: 5,
    tokenCount: null,
    error: false,
    errorMessage: null,
  },
];

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('MetricsPage', () => {
  it('shows loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<MetricsPage />);
    expect(screen.getByText('Loading metrics...')).toBeInTheDocument();
  });

  it('renders "No data yet" when API returns empty summary', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              totalQueries: 0,
              avgLatencyMs: 0,
              p50LatencyMs: 0,
              p95LatencyMs: 0,
              avgRelevanceScore: 0,
              errorRate: 0,
              queriesPerDay: [],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      });
    });

    render(<MetricsPage />);

    await waitFor(() => {
      expect(screen.getByText('No data yet')).toBeInTheDocument();
    });
  });

  it('renders metric cards with data', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockRecent),
      });
    });

    render(<MetricsPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Queries')).toBeInTheDocument();
    });

    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('251 ms')).toBeInTheDocument(); // 250.5 rounded
    expect(screen.getByText('800 ms')).toBeInTheDocument();
    expect(screen.getByText('0.823')).toBeInTheDocument();
    expect(screen.getByText('4.8%')).toBeInTheDocument();
  });

  it('renders chart containers', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockRecent),
      });
    });

    render(<MetricsPage />);

    await waitFor(() => {
      expect(screen.getByText('Queries Per Day')).toBeInTheDocument();
    });

    expect(screen.getByTestId('queries-per-day-chart')).toBeInTheDocument();
    expect(screen.getByTestId('latency-distribution-chart')).toBeInTheDocument();
    expect(screen.getByTestId('relevance-over-time-chart')).toBeInTheDocument();
  });

  it('displays error when fetch fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
    });

    render(<MetricsPage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load metrics')).toBeInTheDocument();
    });
  });
});
