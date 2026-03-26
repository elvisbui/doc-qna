import { corsHeaders, type Env, type ChunkData } from "./types";

const SYSTEM_PROMPT = `You are a helpful document Q&A assistant. Answer questions based on the provided context from uploaded documents.

Rules:
- Only answer based on the provided context
- Cite your sources using [1], [2], etc. corresponding to the context chunks
- If the context doesn't contain enough information, say "I don't have enough information in the uploaded documents to answer this question."
- Be concise and accurate`;

export const onRequestPost: PagesFunction<Env> = async (context) => {
  const { AI, VECTORIZE, KV } = context.env;
  const body = (await context.request.json()) as {
    query: string;
    history?: { role: string; content: string }[];
    documentIds?: string[];
  };
  const { query, history = [], documentIds } = body;

  const encoder = new TextEncoder();
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();

  const sendEvent = async (event: string, data: string) => {
    await writer.write(encoder.encode(`event: ${event}\ndata: ${data}\n\n`));
  };

  (async () => {
    const startTime = Date.now();
    let hasError = false;
    let avgRelevance = 0;
    try {
      // 1. Embed the query
      const embeddingResult = await AI.run("@cf/baai/bge-base-en-v1.5", {
        text: [query],
      });
      const queryVector = embeddingResult.data[0];

      // 2. Search Vectorize for relevant chunks
      // Note: metadata filtering requires a metadata index on the property.
      // We query all vectors and filter by documentIds client-side if needed.
      const searchResults = await VECTORIZE.query(queryVector, {
        topK: 20,
        returnMetadata: "all",
      });

      // 3. Retrieve chunk text from KV and build citations (camelCase for frontend)
      const citations: {
        documentId: string;
        documentName: string;
        chunkContent: string;
        chunkIndex: number;
        relevanceScore: number;
        pageNumber: number | null;
      }[] = [];
      let contextText = "";

      for (const match of searchResults.matches) {
        if (citations.length >= 5) break;
        const chunkKey = `chunk:${match.id}`;
        const chunkJson = await KV.get(chunkKey);
        if (chunkJson) {
          const raw = JSON.parse(chunkJson);
          const chunk: ChunkData = {
            id: raw.id || "",
            documentId: raw.documentId || raw.document_id || "",
            text: raw.text || "",
            chunkIndex: raw.chunkIndex ?? raw.chunk_index ?? 0,
            pageNumber: raw.pageNumber ?? raw.page_number ?? null,
          };
          // Client-side document filter
          if (documentIds && documentIds.length > 0 && !documentIds.includes(chunk.documentId)) {
            continue;
          }
          const docJson = await KV.get(`doc:${chunk.documentId}`);
          const docName = docJson ? JSON.parse(docJson).filename : "Unknown";

          citations.push({
            documentId: chunk.documentId,
            documentName: docName,
            chunkContent: chunk.text,
            chunkIndex: chunk.chunkIndex,
            relevanceScore: match.score,
            pageNumber: chunk.pageNumber,
          });

          contextText += `[${citations.length}] (${docName}): ${chunk.text}\n\n`;
        }
      }

      // Track average relevance
      if (citations.length > 0) {
        avgRelevance =
          citations.reduce((sum, c) => sum + c.relevanceScore, 0) /
          citations.length;
      }

      // 4. Send citations
      await sendEvent("citations", JSON.stringify(citations));

      // 5. Build messages for LLM
      const messages: { role: string; content: string }[] = [
        { role: "system", content: SYSTEM_PROMPT },
      ];

      if (contextText) {
        messages.push({
          role: "system",
          content: `Context from uploaded documents:\n\n${contextText}`,
        });
      }

      const recentHistory = history.slice(-6);
      for (const msg of recentHistory) {
        messages.push({ role: msg.role, content: msg.content });
      }
      messages.push({ role: "user", content: query });

      // 6. Stream LLM response
      const stream = await AI.run("@cf/meta/llama-3.3-70b-instruct-fp8-fast", {
        messages,
        stream: true,
      });

      const reader = (stream as ReadableStream).getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ") && line !== "data: [DONE]") {
            try {
              const parsed = JSON.parse(line.slice(6));
              if (parsed.response) {
                await sendEvent("token", parsed.response);
              }
            } catch {
              // Skip unparseable lines
            }
          }
        }
      }

      await sendEvent("done", "");
    } catch (err) {
      hasError = true;
      await sendEvent("error", (err as Error).message);
    } finally {
      // Record metrics
      try {
        const latencyMs = Date.now() - startTime;
        const raw = await KV.get("metrics_log");
        const entries = raw ? JSON.parse(raw) : [];
        entries.push({
          timestamp: new Date().toISOString(),
          latencyMs,
          relevanceScore: Math.round(avgRelevance * 100) / 100,
          error: hasError,
        });
        // Keep last 500 entries
        const trimmed = entries.slice(-500);
        await KV.put("metrics_log", JSON.stringify(trimmed));
      } catch {
        // Don't fail the request if metrics recording fails
      }
      await writer.close();
    }
  })();

  return new Response(readable, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      ...corsHeaders(),
    },
  });
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
