import { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import type { MetricsSummary, QueryMetric } from '@/types';

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
        setError('Could not load metrics.');
      } finally {
        setLoading(false);
      }
    }
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading metrics…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-600 dark:text-gray-300">{error}</p>
      </div>
    );
  }

  const isEmpty = !summary || summary.totalQueries === 0;

  if (isEmpty) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <header className="mb-10">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Metrics</h1>
        </header>
        <div className="py-16 text-center">
          <p className="text-sm text-gray-900 dark:text-gray-100">No data yet</p>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Ask a question in the chat to start collecting metrics.
          </p>
        </div>
      </div>
    );
  }

  const latencyBuckets = buildLatencyBuckets(recent);

  const relevanceOverTime = [...recent]
    .filter((m) => !m.error)
    .sort((a, b) => a.timestamp - b.timestamp)
    .map((m) => ({
      time: new Date(m.timestamp * 1000).toLocaleDateString(),
      relevance: Math.round(m.avgRelevanceScore * 1000) / 1000,
    }));

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      <header className="mb-10">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Metrics</h1>
      </header>

      <StatRow
        stats={[
          { label: 'Total queries', value: String(summary!.totalQueries) },
          { label: 'Avg latency', value: formatMs(summary!.avgLatencyMs) },
          { label: 'p95 latency', value: formatMs(summary!.p95LatencyMs) },
          { label: 'Avg relevance', value: summary!.avgRelevanceScore.toFixed(3) },
          { label: 'Error rate', value: `${(summary!.errorRate * 100).toFixed(1)}%` },
        ]}
      />

      <div className="space-y-12 mt-12">
        <ChartBlock title="Queries per day" testId="queries-per-day-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={summary!.queriesPerDay} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                axisLine={false}
                tickLine={false}
                className="text-gray-500 dark:text-gray-400"
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: 'currentColor' }}
                axisLine={false}
                tickLine={false}
                className="text-gray-500 dark:text-gray-400"
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ stroke: 'rgba(0,0,0,0.1)', strokeWidth: 1 }}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="currentColor"
                strokeWidth={1.5}
                dot={{ r: 3, strokeWidth: 0, fill: 'currentColor' }}
                activeDot={{ r: 4, strokeWidth: 0, fill: 'currentColor' }}
                className="text-gray-900 dark:text-gray-100"
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartBlock>

        <ChartBlock title="Latency distribution" testId="latency-distribution-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={latencyBuckets} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <XAxis
                dataKey="range"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                axisLine={false}
                tickLine={false}
                className="text-gray-500 dark:text-gray-400"
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: 'currentColor' }}
                axisLine={false}
                tickLine={false}
                className="text-gray-500 dark:text-gray-400"
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ fill: 'rgba(0,0,0,0.04)' }}
              />
              <Bar
                dataKey="count"
                fill="currentColor"
                radius={[2, 2, 0, 0]}
                className="text-gray-900 dark:text-gray-100"
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartBlock>

        <ChartBlock title="Relevance over time" testId="relevance-over-time-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={relevanceOverTime} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <XAxis
                dataKey="time"
                tick={{ fontSize: 11, fill: 'currentColor' }}
                axisLine={false}
                tickLine={false}
                className="text-gray-500 dark:text-gray-400"
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fontSize: 11, fill: 'currentColor' }}
                axisLine={false}
                tickLine={false}
                className="text-gray-500 dark:text-gray-400"
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ stroke: 'rgba(0,0,0,0.1)', strokeWidth: 1 }}
              />
              <Line
                type="monotone"
                dataKey="relevance"
                stroke="currentColor"
                strokeWidth={1.5}
                dot={{ r: 3, strokeWidth: 0, fill: 'currentColor' }}
                activeDot={{ r: 4, strokeWidth: 0, fill: 'currentColor' }}
                className="text-gray-900 dark:text-gray-100"
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartBlock>
      </div>
    </div>
  );
}

const tooltipStyle: React.CSSProperties = {
  background: 'rgba(23, 23, 23, 0.92)',
  border: 'none',
  borderRadius: 8,
  padding: '6px 10px',
  color: '#fff',
  fontSize: 12,
  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
};

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${ms.toFixed(0)}ms`;
}

function buildLatencyBuckets(metrics: QueryMetric[]) {
  const buckets = [
    { range: '<100ms', min: 0, max: 100, count: 0 },
    { range: '100–500ms', min: 100, max: 500, count: 0 },
    { range: '500ms–1s', min: 500, max: 1000, count: 0 },
    { range: '1–3s', min: 1000, max: 3000, count: 0 },
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

function StatRow({ stats }: { stats: { label: string; value: string }[] }) {
  return (
    <dl className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-x-8 gap-y-6 border-t border-gray-200 dark:border-white/10 pt-6">
      {stats.map((s) => (
        <div key={s.label} className="min-w-0">
          <dt className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {s.label}
          </dt>
          <dd className="mt-1 text-2xl font-semibold tabular-nums text-gray-900 dark:text-gray-100 truncate">
            {s.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ChartBlock({
  title,
  testId,
  children,
}: {
  title: string;
  testId: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
        {title}
      </h2>
      <div className="h-60" data-testid={testId}>
        {children}
      </div>
    </section>
  );
}
