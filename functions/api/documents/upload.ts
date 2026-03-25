import { extractText, getDocumentProxy } from "unpdf";
import { corsHeaders, jsonResponse, type Env, type DocumentMeta, type ChunkData } from "../types";

async function extractFileText(file: File): Promise<string> {
  const ext = file.name.split(".").pop()?.toLowerCase() || "txt";
  if (ext === "pdf") {
    const buffer = await file.arrayBuffer();
    const pdf = await getDocumentProxy(new Uint8Array(buffer));
    const { text } = await extractText(pdf, { mergePages: true });
    return text;
  }
  return await file.text();
}

export const onRequestPost: PagesFunction<Env> = async (context) => {
  const { AI, VECTORIZE, KV } = context.env;

  const formData = await context.request.formData();
  const file = formData.get("file") as File | null;
  if (!file) {
    return jsonResponse({ error: "No file provided" }, 400);
  }

  const docId = crypto.randomUUID();
  const text = await extractFileText(file);
  const ext = file.name.split(".").pop() || "txt";

  const meta: DocumentMeta = {
    id: docId,
    filename: file.name,
    fileType: ext,
    fileSize: file.size,
    status: "processing",
    createdAt: new Date().toISOString(),
    chunkCount: 0,
  };
  await KV.put(`doc:${docId}`, JSON.stringify(meta));

  const docListJson = await KV.get("doc_list");
  const docIds: string[] = docListJson ? JSON.parse(docListJson) : [];
  docIds.push(docId);
  await KV.put("doc_list", JSON.stringify(docIds));

  const chunks = chunkText(text, 500, 50);

  try {
    const chunkTexts = chunks.map((c) => c.text);
    const allVectors: { id: string; values: number[]; metadata: Record<string, string | number> }[] = [];

    for (let i = 0; i < chunkTexts.length; i += 20) {
      const batch = chunkTexts.slice(i, i + 20);
      const embResult = await AI.run("@cf/baai/bge-base-en-v1.5", { text: batch });

      const kvWrites: Promise<void>[] = [];
      for (let j = 0; j < batch.length; j++) {
        const chunkIndex = i + j;
        const chunkId = `${docId}_${chunkIndex}`;

        const chunkData: ChunkData = {
          id: chunkId,
          documentId: docId,
          text: chunks[chunkIndex].text,
          chunkIndex,
          pageNumber: null,
        };
        kvWrites.push(KV.put(`chunk:${chunkId}`, JSON.stringify(chunkData)));

        allVectors.push({
          id: chunkId,
          values: embResult.data[j],
          metadata: { document_id: docId },
        });
      }
      await Promise.all(kvWrites);
    }

    if (allVectors.length > 0) {
      await VECTORIZE.upsert(allVectors);
    }

    meta.status = "ready";
    meta.chunkCount = chunks.length;
    await KV.put(`doc:${docId}`, JSON.stringify(meta));
  } catch (err) {
    meta.status = "error";
    await KV.put(`doc:${docId}`, JSON.stringify(meta));
    console.error("Ingestion error:", err);
  }

  return jsonResponse({ document_id: docId, filename: file.name, status: meta.status }, 202);
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};

function chunkText(text: string, size: number, overlap: number): { text: string }[] {
  const chunks: { text: string }[] = [];
  let start = 0;
  while (start < text.length) {
    const end = Math.min(start + size, text.length);
    const t = text.slice(start, end).trim();
    if (t.length > 0) chunks.push({ text: t });
    start += size - overlap;
  }
  return chunks;
}
