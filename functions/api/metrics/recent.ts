import { corsHeaders, jsonResponse, type Env } from "../types";

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { KV } = context.env;

  const raw = await KV.get("metrics_log");
  const entries = raw ? JSON.parse(raw) : [];

  // Return last 50 entries
  return jsonResponse(entries.slice(-50));
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
