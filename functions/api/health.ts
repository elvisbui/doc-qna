import { jsonResponse, type Env } from "./types";

export const onRequestGet: PagesFunction<Env> = async () => {
  return jsonResponse({
    status: "healthy",
    version: "0.1.0",
    dependencies: {
      chromadb: { status: "up", detail: "cloudflare vectorize" },
      llm: { status: "up", detail: "cloudflare workers ai" },
      embedder: { status: "up", detail: "cloudflare workers ai embeddings" },
    },
  });
};
