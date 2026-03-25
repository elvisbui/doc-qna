import { jsonResponse, type Env, type DocumentMeta } from "../types";

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

// GET /api/documents — list all documents
export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { KV } = context.env;
  const docListJson = await KV.get("doc_list");
  const docIds: string[] = docListJson ? JSON.parse(docListJson) : [];

  const documents: DocumentMeta[] = [];
  for (const id of docIds) {
    const docJson = await KV.get(`doc:${id}`);
    if (docJson) {
      documents.push(normalizeDoc(JSON.parse(docJson)));
    }
  }

  return jsonResponse({ documents, total: documents.length });
};
