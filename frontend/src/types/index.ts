/** Processing state of an uploaded document. */
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'error';

/** Represents an uploaded document and its processing metadata. */
export interface Document {
  /** Unique identifier for the document. */
  id: string;
  /** Original filename of the uploaded file. */
  filename: string;
  /** MIME type or extension of the file (e.g., "pdf", "docx"). */
  fileType: string;
  /** File size in bytes. */
  fileSize: number;
  /** Current processing status of the document. */
  status: DocumentStatus;
  /** ISO 8601 timestamp of when the document was uploaded. */
  createdAt: string;
  /** Error details if the document failed processing. */
  errorMessage?: string;
}

/** A source citation referencing a specific chunk from a retrieved document. */
export interface Citation {
  /** ID of the source document. */
  documentId: string;
  /** Display name of the source document. */
  documentName: string;
  /** Text content of the retrieved chunk. */
  chunkContent: string;
  /** Zero-based index of the chunk within the document. */
  chunkIndex: number;
  /** Similarity score between the query and this chunk (0-1). */
  relevanceScore: number;
  /** Page number in the original document, if available (PDF only). */
  pageNumber?: number;
}

/** Role of a participant in a chat conversation. */
export type ChatRole = 'user' | 'assistant';

/** A single message in a chat conversation. */
export interface ChatMessage {
  /** Whether this message is from the user or the assistant. */
  role: ChatRole;
  /** Text content of the message. */
  content: string;
}

/** Response returned by the document upload API. */
export interface UploadResponse {
  /** Unique identifier assigned to the uploaded document. */
  documentId: string;
  /** Original filename of the uploaded file. */
  filename: string;
  /** Initial processing status after upload. */
  status: DocumentStatus;
}

/** Preview of a document's text content. */
export interface DocumentPreview {
  /** Extracted text content (may be truncated). */
  content: string;
  /** Whether the content was truncated due to length. */
  truncated: boolean;
  /** Total character length of the full document text. */
  totalLength: number;
}

/** Schema definition for a single plugin configuration field. */
export interface PluginConfigField {
  /** Machine-readable field identifier. */
  name: string;
  /** Data type of the configuration field. */
  fieldType: 'string' | 'number' | 'boolean' | 'select';
  /** Default value for the field. */
  default: unknown;
  /** Human-readable label for display in the UI. */
  label: string;
  /** Help text describing the field's purpose. */
  description: string;
  /** Available options when fieldType is 'select'. */
  options?: string[];
}

/** Installed plugin with its metadata and activation state. */
export interface Plugin {
  /** Unique plugin name (used as identifier). */
  name: string;
  /** Semantic version of the plugin. */
  version: string;
  /** Human-readable description of the plugin's functionality. */
  description: string;
  /** Whether the plugin is currently active. */
  enabled: boolean;
  /** Configuration schema for the plugin's settings, if configurable. */
  configSchema?: PluginConfigField[];
}

/** Plugin configuration state with its current values and schema. */
export interface PluginConfig {
  /** Plugin name this configuration belongs to. */
  name: string;
  /** Current configuration key-value pairs. */
  config: Record<string, unknown>;
  /** Schema defining available configuration fields. */
  configSchema: PluginConfigField[];
}

/** A knowledge pack that can be installed to provide pre-loaded documents. */
export interface Pack {
  /** Unique name identifier for the pack. */
  name: string;
  /** Semantic version of the pack. */
  version: string;
  /** Human-readable description of the pack's contents. */
  description: string;
  /** Number of documents included in the pack. */
  docCount: number;
  /** Whether the pack is currently installed. */
  installed: boolean;
  /** Version of the currently installed pack, if any. */
  installedVersion?: string | null;
  /** Example queries that work well with this pack's documents. */
  suggestedQueries: string[];
}

/** A trace entry recording a plugin's execution during a request. */
export interface PluginTraceEntry {
  /** Name of the plugin that was executed. */
  pluginName: string;
  /** Hook that triggered the plugin (e.g., "on_retrieve", "on_generate"). */
  hookName: string;
  /** Execution time of the plugin in milliseconds. */
  durationMs: number;
  /** Whether the plugin execution resulted in an error. */
  error: boolean;
}

/** Aggregated metrics summary for the observability dashboard. */
export interface MetricsSummary {
  /** Total number of queries processed. */
  totalQueries: number;
  /** Average query latency in milliseconds. */
  avgLatencyMs: number;
  /** Median (50th percentile) query latency in milliseconds. */
  p50LatencyMs: number;
  /** 95th percentile query latency in milliseconds. */
  p95LatencyMs: number;
  /** Average relevance score across all queries (0-1). */
  avgRelevanceScore: number;
  /** Fraction of queries that resulted in errors (0-1). */
  errorRate: number;
  /** Daily query counts for time-series charting. */
  queriesPerDay: { date: string; count: number }[];
}

/** Individual query metric recorded for observability. */
export interface QueryMetric {
  /** Auto-incrementing metric record ID. */
  id: number;
  /** Unix timestamp of when the query was processed. */
  timestamp: number;
  /** The user's query text. */
  queryText: string;
  /** Total query processing latency in milliseconds. */
  latencyMs: number;
  /** Average relevance score of retrieved chunks (0-1). */
  avgRelevanceScore: number;
  /** Number of chunks retrieved from the vector store. */
  numChunksRetrieved: number;
  /** Number of tokens used in the LLM response, if available. */
  tokenCount: number | null;
  /** Whether the query resulted in an error. */
  error: boolean;
  /** Error message if the query failed. */
  errorMessage: string | null;
}

/** Application settings for LLM providers, chunking, and retrieval configuration. */
export interface Settings {
  /** Active LLM provider (e.g., "ollama", "openai", "anthropic"). */
  llmProvider: string;
  /** Base URL for the Ollama API server. */
  ollamaBaseUrl: string;
  /** Model name to use with Ollama. */
  ollamaModel: string;
  /** Active embedding provider. */
  embeddingProvider: string;
  /** Model name to use for embeddings. */
  embeddingModel: string;
  /** Document chunking strategy (e.g., "recursive", "fixed"). */
  chunkingStrategy: string;
  /** Retrieval strategy (e.g., "vector", "hybrid"). */
  retrievalStrategy: string;
  /** Maximum number of characters per chunk. */
  chunkSize: number;
  /** Number of overlapping characters between adjacent chunks. */
  chunkOverlap: number;
  /** Backend logging level. */
  logLevel: string;
  /** Whether an OpenAI API key is configured. */
  hasOpenaiKey: boolean;
  /** Whether an Anthropic API key is configured. */
  hasAnthropicKey: boolean;
  /** Whether a Cloudflare Workers AI token is configured. */
  hasCloudflareToken: boolean;
  /** Masked hint of the configured OpenAI key. */
  openaiKeyHint: string;
  /** Masked hint of the configured Anthropic key. */
  anthropicKeyHint: string;
  /** Masked hint of the configured Cloudflare token. */
  cloudflareKeyHint: string;
  /** System prompt sent to the LLM with every request. */
  systemPrompt: string;
  /** LLM temperature parameter controlling response randomness (0-2). */
  llmTemperature: number;
  /** LLM top-p (nucleus sampling) parameter (0-1). */
  llmTopP: number;
  /** Maximum number of tokens the LLM may generate per response. */
  llmMaxTokens: number;
}
