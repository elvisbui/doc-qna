import { jsonResponse } from "./types";

export const onRequestGet: PagesFunction = async () => {
  return jsonResponse({
    plugins: [
      { name: "query_rewriter", enabled: false, description: "Rewrites queries for better retrieval" },
      { name: "pii_redactor", enabled: false, description: "Redacts personally identifiable information" },
      { name: "reranker", enabled: false, description: "Re-ranks retrieved chunks for relevance" },
      { name: "summarizer", enabled: false, description: "Summarizes long documents on ingestion" },
    ],
  });
};
