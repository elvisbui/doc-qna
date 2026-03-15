# doc-qna

**Upload documents. Ask questions. Get cited answers.**

A Retrieval-Augmented Generation (RAG) system that lets users upload documents and ask natural-language questions, receiving accurate, cited answers grounded in their own data -- not hallucinated internet responses. Runs entirely on your own hardware with Ollama at zero cost, or connects to OpenAI / Anthropic APIs.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS v4 |
| Backend | Python 3.13, FastAPI |
| Vector DB | ChromaDB (embedded mode, no separate server) |
| LLM Providers | Ollama, OpenAI, Anthropic |

## License

[MIT](LICENSE) -- Copyright (c) Elvis Bui
