import { corsHeaders, jsonResponse, type Env, type ChunkData } from "../../types";

const GITHUB_RAW =
  "https://raw.githubusercontent.com/elvisbui/doc-qna/main/packs";

const PACK_MANIFESTS: Record<
  string,
  { documents: string[]; version: string }
> = {
  "ml-basics": {
    version: "1.0.0",
    documents: [
      "documents/machine-learning-basics.md",
      "documents/neural-networks.md",
      "documents/data-preprocessing.md",
    ],
  },
  "python-basics": {
    version: "1.0.0",
    documents: [
      "documents/variables-and-types.md",
      "documents/functions.md",
      "documents/classes.md",
      "documents/modules.md",
    ],
  },
};

function chunkText(
  text: string,
  size: number,
  overlap: number,
): { text: string }[] {
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

export const onRequestPost: PagesFunction<Env> = async (context) => {
  try {
    const { AI, VECTORIZE, KV } = context.env;
    const packName = context.params.name as string;

    const manifest = PACK_MANIFESTS[packName];
    if (!manifest) {
      return jsonResponse({ error: `Unknown pack: ${packName}` }, 404);
    }

    // Check if already installed
    const registryJson = await KV.get("pack_registry");
    const registry = registryJson
      ? JSON.parse(registryJson)
      : { installed: [], versions: {} };
    if (registry.installed.includes(packName)) {
      return jsonResponse({ message: "Already installed" });
    }

    const allVectors: {
      id: string;
      values: number[];
      metadata: Record<string, string>;
    }[] = [];

    for (const docPath of manifest.documents) {
      const url = `${GITHUB_RAW}/${packName}/${docPath}`;
      const resp = await fetch(url);
      if (!resp.ok) continue;
      const text = await resp.text();
      const filename = docPath.split("/").pop() || docPath;

      // Create a document entry
      const docId = `pack_${packName}_${filename}`;
      await KV.put(
        `doc:${docId}`,
        JSON.stringify({
          id: docId,
          filename,
          fileType: "md",
          fileSize: text.length,
          status: "ready",
          createdAt: new Date().toISOString(),
          chunkCount: 0,
          packName,
        }),
      );

      const chunks = chunkText(text, 500, 50);
      const chunkTexts = chunks.map((c) => c.text);

      for (let i = 0; i < chunkTexts.length; i += 20) {
        const batch = chunkTexts.slice(i, i + 20);
        const embResult = await AI.run("@cf/baai/bge-base-en-v1.5", {
          text: batch,
        });

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
          kvWrites.push(
            KV.put(`chunk:${chunkId}`, JSON.stringify(chunkData)),
          );

          allVectors.push({
            id: chunkId,
            values: embResult.data[j],
            metadata: { document_id: docId, pack_name: packName },
          });
        }
        await Promise.all(kvWrites);
      }

      // Update chunk count
      const docMeta = JSON.parse((await KV.get(`doc:${docId}`)) || "{}");
      docMeta.chunkCount = chunks.length;
      await KV.put(`doc:${docId}`, JSON.stringify(docMeta));
    }

    if (allVectors.length > 0) {
      await VECTORIZE.upsert(allVectors);
    }

    // Update registry
    registry.installed.push(packName);
    registry.versions[packName] = manifest.version;
    await KV.put("pack_registry", JSON.stringify(registry));

    return jsonResponse({ installed: true, pack: packName });
  } catch (err) {
    return jsonResponse({ error: (err as Error).message }, 500);
  }
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
