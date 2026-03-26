import { jsonResponse } from "../types";

export const onRequestGet: PagesFunction = async () => {
  return jsonResponse({
    totalQueries: 0,
    avgLatencyMs: 0,
    p50LatencyMs: 0,
    p95LatencyMs: 0,
    avgRelevanceScore: 0,
    errorRate: 0,
    queriesPerDay: [],
  });
};
