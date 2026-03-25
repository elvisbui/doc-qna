export interface Env {
  AI: Ai;
  VECTORIZE: VectorizeIndex;
  KV: KVNamespace;
}

export interface DocumentMeta {
  id: string;
  filename: string;
  fileType: string;
  fileSize: number;
  status: "pending" | "processing" | "ready" | "error";
  createdAt: string;
  chunkCount: number;
}

export interface ChunkData {
  id: string;
  documentId: string;
  text: string;
  chunkIndex: number;
  pageNumber: number | null;
}

export function corsHeaders(): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}
