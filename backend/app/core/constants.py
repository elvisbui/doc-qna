"""Project-wide constants."""

# Application version — single source of truth
APP_VERSION: str = "0.1.0"

# Maximum upload file size: 50 MB
MAX_FILE_SIZE: int = 50 * 1024 * 1024

# Chunking parameters (characters)
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200

# Retrieval: top-k chunks per query
MAX_CHUNKS_PER_QUERY: int = 5

# ChromaDB collection name
COLLECTION_NAME: str = "doc_qna_embeddings"

# Maximum tokens for LLM response generation
MAX_RESPONSE_TOKENS: int = 16384

# Maximum number of chat history messages to send to the LLM
MAX_HISTORY_MESSAGES: int = 10

# Maximum characters for document preview endpoint
PREVIEW_MAX_CHARS: int = 5000

# System prompt template for RAG LLM providers
SYSTEM_PROMPT_TEMPLATE = (
    "Use the following context to answer the question. "
    "Cite your sources using [1], [2], etc. corresponding to the source numbers below. "
    "If the context does not contain enough information, say so.\n\n"
    "Context:\n{context}"
)
