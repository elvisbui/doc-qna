import { corsHeaders, jsonResponse, type Env } from "../types";

const DEFAULT_SETTINGS = {
  llmProvider: "cloudflare",
  ollamaBaseUrl: "http://localhost:11434",
  ollamaModel: "llama3.2",
  embeddingProvider: "cloudflare",
  embeddingModel: "@cf/baai/bge-base-en-v1.5",
  chunkingStrategy: "fixed",
  retrievalStrategy: "vector",
  chunkSize: 500,
  chunkOverlap: 50,
  logLevel: "INFO",
  hasOpenaiKey: false,
  hasAnthropicKey: false,
  hasCloudflareToken: true,
  openaiKeyHint: "",
  anthropicKeyHint: "",
  cloudflareKeyHint: "****",
  systemPrompt: "",
  llmTemperature: 0.7,
  llmTopP: 1.0,
  llmMaxTokens: 2048,
};

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { KV } = context.env;
  const stored = await KV.get("settings");
  const settings = stored ? { ...DEFAULT_SETTINGS, ...JSON.parse(stored) } : DEFAULT_SETTINGS;
  return jsonResponse(settings);
};

export const onRequestPut: PagesFunction<Env> = async (context) => {
  const { KV } = context.env;
  const body = await context.request.json();
  const stored = await KV.get("settings");
  const current = stored ? { ...DEFAULT_SETTINGS, ...JSON.parse(stored) } : DEFAULT_SETTINGS;
  const updated = { ...current, ...body };
  await KV.put("settings", JSON.stringify(updated));
  return jsonResponse(updated);
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
