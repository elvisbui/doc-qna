import { corsHeaders, jsonResponse, type Env, type DocumentMeta } from "../types";

function normalizeDoc(raw: Record<string, unknown>): DocumentMeta {
  return {
    id: (raw.id as string) || "",
    filename: (raw.filename as string) || "",
    fileType: (raw.fileType ?? raw.file_type ?? "txt") as string,
    fileSize: (raw.fileSize ?? raw.file_size ?? 0) as number,
    status: (raw.status as DocumentMeta["status"]) || "ready",
    createdAt: (raw.createdAt ?? raw.created_at ?? "") as string,
    chunkCount: (raw.chunkCount ?? raw.chunk_count ?? 0) as number,
  };
}

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { KV } = context.env;
  const docId = context.params.id as string;
  const docJson = await KV.get(`doc:${docId}`);
  if (!docJson) {
    return jsonResponse({ error: "Document not found" }, 404);
  }
  return jsonResponse(normalizeDoc(JSON.parse(docJson)));
};

export const onRequestDelete: PagesFunction<Env> = async (context) => {
  try {
    const { KV, VECTORIZE } = context.env;
    const docId = context.params.id as string;

    const docJson = await KV.get(`doc:${docId}`);
    if (!docJson) {
      return jsonResponse({ error: "Document not found" }, 404);
    }
    const doc = JSON.parse(docJson);

    const chunkIds: string[] = [];
    for (let i = 0; i < (doc.chunkCount || 0); i++) {
      chunkIds.push(`${docId}_${i}`);
    }

    // Delete KV entries in parallel batches of 10
    for (let i = 0; i < chunkIds.length; i += 10) {
      const batch = chunkIds.slice(i, i + 10);
      await Promise.all(batch.map((id) => KV.delete(`chunk:${id}`)));
    }

    // Delete vectors in batches of 100
    for (let i = 0; i < chunkIds.length; i += 100) {
      const batch = chunkIds.slice(i, i + 100);
      try {
        await VECTORIZE.deleteByIds(batch);
      } catch {
        // Vectorize delete may fail if vectors don't exist, ignore
      }
    }

    await KV.delete(`doc:${docId}`);

    const docListJson = await KV.get("doc_list");
    const docIds: string[] = docListJson ? JSON.parse(docListJson) : [];
    await KV.put("doc_list", JSON.stringify(docIds.filter((id) => id !== docId)));

    return jsonResponse({ deleted: true });
  } catch (err) {
    return jsonResponse({ error: (err as Error).message }, 500);
  }
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
