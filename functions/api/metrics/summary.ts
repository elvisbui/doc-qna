import { corsHeaders, jsonResponse, type Env } from "../types";

interface MetricEntry {
  timestamp: string;
  latencyMs: number;
  relevanceScore: number;
  error: boolean;
}

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { KV } = context.env;

  const raw = await KV.get("metrics_log");
  const entries: MetricEntry[] = raw ? JSON.parse(raw) : [];

  if (entries.length === 0) {
    return jsonResponse({
      totalQueries: 0,
      avgLatencyMs: 0,
      p50LatencyMs: 0,
      p95LatencyMs: 0,
      avgRelevanceScore: 0,
      errorRate: 0,
      queriesPerDay: [],
    });
  }

  const latencies = entries.map((e) => e.latencyMs).sort((a, b) => a - b);
  const relevances = entries.map((e) => e.relevanceScore);
  const errors = entries.filter((e) => e.error).length;

  const avgLatency =
    latencies.reduce((a, b) => a + b, 0) / latencies.length;
  const avgRelevance =
    relevances.reduce((a, b) => a + b, 0) / relevances.length;
  const p50 = latencies[Math.floor(latencies.length * 0.5)];
  const p95 = latencies[Math.floor(latencies.length * 0.95)];

  // Group by day
  const dayCounts: Record<string, number> = {};
  for (const e of entries) {
    const day = e.timestamp.slice(0, 10);
    dayCounts[day] = (dayCounts[day] || 0) + 1;
  }
  const queriesPerDay = Object.entries(dayCounts)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date, count }));

  return jsonResponse({
    totalQueries: entries.length,
    avgLatencyMs: Math.round(avgLatency),
    p50LatencyMs: Math.round(p50),
    p95LatencyMs: Math.round(p95),
    avgRelevanceScore: Math.round(avgRelevance * 100) / 100,
    errorRate: Math.round((errors / entries.length) * 100) / 100,
    queriesPerDay,
  });
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
