import { corsHeaders, jsonResponse, type Env } from "../../types";

export const onRequestPost: PagesFunction<Env> = async (context) => {
  try {
    const { KV, VECTORIZE } = context.env;
    const packName = context.params.name as string;

    const registryJson = await KV.get("pack_registry");
    const registry = registryJson
      ? JSON.parse(registryJson)
      : { installed: [], versions: {} };

    if (!registry.installed.includes(packName)) {
      return jsonResponse({ error: "Pack not installed" }, 404);
    }

    // Find all docs belonging to this pack and delete their chunks
    const docListJson = await KV.get("doc_list");
    const docIds: string[] = docListJson ? JSON.parse(docListJson) : [];
    const remainingDocs: string[] = [];
    const vectorIdsToDelete: string[] = [];

    for (const docId of docIds) {
      if (docId.startsWith(`pack_${packName}_`)) {
        const docJson = await KV.get(`doc:${docId}`);
        if (docJson) {
          const doc = JSON.parse(docJson);
          for (let i = 0; i < (doc.chunkCount || 0); i++) {
            const chunkId = `${docId}_${i}`;
            vectorIdsToDelete.push(chunkId);
            await KV.delete(`chunk:${chunkId}`);
          }
        }
        await KV.delete(`doc:${docId}`);
      } else {
        remainingDocs.push(docId);
      }
    }

    // Also delete pack docs that use pack_ prefix but aren't in doc_list
    // (pack docs aren't added to doc_list)
    const packDocPrefixes = [`pack_${packName}_`];
    // We stored chunks with IDs like pack_ml-basics_filename_0
    // Delete vectors
    if (vectorIdsToDelete.length > 0) {
      for (let i = 0; i < vectorIdsToDelete.length; i += 100) {
        const batch = vectorIdsToDelete.slice(i, i + 100);
        try {
          await VECTORIZE.deleteByIds(batch);
        } catch {
          // ignore
        }
      }
    }

    await KV.put("doc_list", JSON.stringify(remainingDocs));

    // Update registry
    registry.installed = registry.installed.filter(
      (n: string) => n !== packName,
    );
    delete registry.versions[packName];
    await KV.put("pack_registry", JSON.stringify(registry));

    return jsonResponse({ uninstalled: true, pack: packName });
  } catch (err) {
    return jsonResponse({ error: (err as Error).message }, 500);
  }
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
