import { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import type { MetricsSummary, QueryMetric } from '@/types';

/** Dashboard page displaying query analytics, latency distribution, and relevance charts. */
export function MetricsPage() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [recent, setRecent] = useState<QueryMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMetrics() {
      setLoading(true);
      setError(null);
      try {
        const [summaryRes, recentRes] = await Promise.all([
          fetch('/api/metrics/summary'),
          fetch('/api/metrics/recent'),
        ]);
        if (!summaryRes.ok || !recentRes.ok) {
          throw new Error('Failed to load metrics');
        }
        const summaryData: MetricsSummary = await summaryRes.json();
        const recentData: QueryMetric[] = await recentRes.json();
        setSummary(summaryData);
        setRecent(recentData);
      } catch {
        setError('Failed to load metrics');
      } finally {
        setLoading(false);
      }
    }
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-gray-500 dark:text-gray-400">Loading metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  const isEmpty = !summary || summary.totalQueries === 0;

  if (isEmpty) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Metrics</h2>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400 text-lg">No data yet</p>
          <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">
            Start asking questions in the Chat tab to see analytics here.
          </p>
        </div>
      </div>
    );
  }

  // Build latency distribution buckets from recent metrics
  const latencyBuckets = buildLatencyBuckets(recent);

  // Build relevance over time (use recent metrics sorted by timestamp ascending)
  const relevanceOverTime = [...recent]
    .filter((m) => !m.error)
    .sort((a, b) => a.timestamp - b.timestamp)
    .map((m) => ({
      time: new Date(m.timestamp * 1000).toLocaleDateString(),
      relevance: Math.round(m.avgRelevanceScore * 1000) / 1000,
    }));

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Metrics</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <MetricCard label="Total Queries" value={String(summary!.totalQueries)} />
        <MetricCard label="Avg Latency" value={`${summary!.avgLatencyMs.toFixed(0)} ms`} />
        <MetricCard label="p95 Latency" value={`${summary!.p95LatencyMs.toFixed(0)} ms`} />
        <MetricCard label="Avg Relevance" value={summary!.avgRelevanceScore.toFixed(3)} />
        <MetricCard label="Error Rate" value={`${(summary!.errorRate * 100).toFixed(1)}%`} />
      </div>

      <div className="space-y-8">
        {/* Chart 1: Queries per day */}
        <Section title="Queries Per Day">
          <div className="h-64" data-testid="queries-per-day-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={summary!.queriesPerDay}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Section>

        {/* Chart 2: Latency distribution */}
        <Section title="Latency Distribution">
          <div className="h-64" data-testid="latency-distribution-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={latencyBuckets}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>

        {/* Chart 3: Relevance over time */}
        <Section title="Relevance Score Over Time">
          <div className="h-64" data-testid="relevance-over-time-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={relevanceOverTime}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 1]} />
                <Tooltip />
                <Line type="monotone" dataKey="relevance" stroke="#10b981" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Section>
      </div>
    </div>
  );
}

/* ---- Helpers ---- */

/**
 * Group query metrics into latency distribution buckets for charting.
 * @param metrics - Array of recent query metrics
 * @returns Array of buckets with range labels and counts
 */
function buildLatencyBuckets(metrics: QueryMetric[]) {
  const buckets = [
    { range: '0-100ms', min: 0, max: 100, count: 0 },
    { range: '100-500ms', min: 100, max: 500, count: 0 },
    { range: '500ms-1s', min: 500, max: 1000, count: 0 },
    { range: '1-3s', min: 1000, max: 3000, count: 0 },
    { range: '3s+', min: 3000, max: Infinity, count: 0 },
  ];
  for (const m of metrics) {
    for (const b of buckets) {
      if (m.latencyMs >= b.min && m.latencyMs < b.max) {
        b.count++;
        break;
      }
    }
  }
  return buckets.map(({ range, count }) => ({ range, count }));
}

/* ---- Sub-components ---- */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
      {children}
    </section>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
    </div>
  );
}
