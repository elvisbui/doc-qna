import { corsHeaders, jsonResponse, type Env } from "./types";

const AVAILABLE_PACKS = [
  {
    name: "ml-basics",
    version: "1.0.0",
    description:
      "Machine Learning basics covering core concepts, neural networks, and data preprocessing.",
    author: "doc-qna",
    license: "MIT",
    doc_count: 3,
    installed: false,
  },
  {
    name: "python-basics",
    version: "1.0.0",
    description:
      "Python fundamentals covering variables, functions, classes, and modules.",
    author: "doc-qna",
    license: "MIT",
    doc_count: 4,
    installed: false,
  },
];

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const { KV } = context.env;
  // Check which packs are installed
  const registryJson = await KV.get("pack_registry");
  const installed: string[] = registryJson
    ? JSON.parse(registryJson).installed || []
    : [];

  const packs = AVAILABLE_PACKS.map((p) => ({
    ...p,
    installed: installed.includes(p.name),
  }));

  return jsonResponse({ packs });
};

export const onRequestOptions: PagesFunction = async () => {
  return new Response(null, { status: 204, headers: corsHeaders() });
};
