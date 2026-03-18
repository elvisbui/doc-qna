import type { Document, DocumentPreview, Pack, Plugin, PluginConfig, Settings, UploadResponse } from '@/types';
import { parseSSEStream } from '@/lib/sse';
import type { SSEEvent } from '@/lib/sse';

const API_BASE = '/api';

/** Custom error class for API responses with non-OK status codes. */
class ApiError extends Error {
  constructor(
    /** HTTP status code from the failed response */
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Parse a fetch Response as JSON, throwing an ApiError if the response is not OK.
 * @param response - The fetch Response to handle
 * @returns The parsed JSON body
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || response.statusText);
  }
  return response.json() as Promise<T>;
}

/**
 * Upload a document file to the server.
 * @param file - The file to upload
 * @returns Upload response containing the new document ID
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<UploadResponse>(response);
}

/**
 * Fetch all documents from the server.
 * @returns Array of document metadata objects
 */
export async function getDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_BASE}/documents`);
  const body = await handleResponse<{ documents: Document[]; total: number }>(response);
  return body.documents;
}

/**
 * Delete a document by ID.
 * @param id - The document ID to delete
 */
export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || response.statusText);
  }
}

/**
 * Fetch a text preview of a document's content.
 * @param documentId - The document ID to preview
 * @returns Preview object with content and truncation info
 */
export async function getDocumentPreview(documentId: string): Promise<DocumentPreview> {
  const response = await fetch(`${API_BASE}/documents/${documentId}/preview`);
  return handleResponse<DocumentPreview>(response);
}

export type { SSEEvent };

/**
 * Send a chat query and stream the response as SSE events.
 * @param query - The user's question
 * @param signal - Optional AbortSignal to cancel the stream
 * @param history - Optional conversation history for context
 * @param documentIds - Optional document IDs to scope the search
 * @returns Async generator yielding SSE events (tokens, citations, done, etc.)
 */
export async function* streamChatMessage(
  query: string,
  signal?: AbortSignal,
  history?: { role: string; content: string }[],
  documentIds?: string[],
): AsyncGenerator<SSEEvent, void, unknown> {
  const body: Record<string, unknown> = { query, history: history ?? [] };
  if (documentIds && documentIds.length > 0) {
    body.documentIds = documentIds;
  }

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const errBody = await response.text();
    throw new ApiError(response.status, errBody || response.statusText);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  yield* parseSSEStream(reader);
}

/** A built-in system prompt preset (e.g., General, Legal Research). */
export interface PromptPreset {
  /** Unique preset identifier */
  id: string;
  /** Human-readable preset name */
  name: string;
  /** Short description of the preset's purpose */
  description: string;
  /** The full system prompt text */
  systemPrompt: string;
}

/**
 * Fetch all available system prompt presets.
 * @returns Array of prompt presets
 */
export async function getPresets(): Promise<PromptPreset[]> {
  const response = await fetch(`${API_BASE}/settings/presets`);
  return handleResponse<PromptPreset[]>(response);
}

/**
 * Fetch the current application settings.
 * @returns The full settings object
 */
export async function getSettings(): Promise<Settings> {
  const response = await fetch(`${API_BASE}/settings`);
  return handleResponse<Settings>(response);
}

/**
 * Update application settings with a partial settings object.
 * @param settings - The fields to update
 * @returns The updated full settings object
 */
export async function updateSettings(settings: Partial<Settings>): Promise<Settings> {
  const response = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  return handleResponse<Settings>(response);
}

/** An Ollama model available on the local Ollama server. */
export interface OllamaModel {
  /** Model name (e.g., "llama3:8b") */
  name: string;
  /** Human-readable model size (e.g., "4.7 GB") */
  size: string;
  /** ISO date of when the model was last modified */
  modified: string;
}

/** Response from the Ollama models endpoint. */
export interface OllamaModelsResponse {
  /** List of available models */
  models: OllamaModel[];
  /** Error message if the Ollama server is unreachable */
  error?: string;
}

/**
 * Fetch the list of models available on the Ollama server.
 * @returns Models response with available models and optional error
 */
export async function getOllamaModels(): Promise<OllamaModelsResponse> {
  const response = await fetch(`${API_BASE}/settings/ollama-models`);
  return handleResponse<OllamaModelsResponse>(response);
}

/** Result of testing connectivity to an LLM provider. */
export interface TestConnectionResult {
  /** Whether the connection succeeded */
  status: 'ok' | 'error';
  /** Human-readable status message */
  message: string;
}

/**
 * Test connectivity to an LLM provider.
 * @param provider - The provider name (e.g., "ollama", "openai")
 * @param config - Optional provider-specific config (e.g., base_url)
 * @returns Connection test result with status and message
 */
export async function testProviderConnection(
  provider: string,
  config: Record<string, string> = {},
): Promise<TestConnectionResult> {
  const response = await fetch(`${API_BASE}/settings/test-connection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, config }),
  });
  return handleResponse<TestConnectionResult>(response);
}

/** Payload for saving one or more API keys. */
export interface ApiKeyUpdate {
  /** OpenAI API key */
  openaiApiKey?: string;
  /** Anthropic API key */
  anthropicApiKey?: string;
  /** Cloudflare Workers AI API token */
  cloudflareApiToken?: string;
  /** Cloudflare account ID */
  cloudflareAccountId?: string;
}

/**
 * Save one or more API keys to the server.
 * @param keys - Object containing the API keys to save
 * @returns The updated settings object
 */
export async function saveApiKeys(keys: ApiKeyUpdate): Promise<Settings> {
  const response = await fetch(`${API_BASE}/settings/api-keys`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(keys),
  });
  return handleResponse<Settings>(response);
}

/**
 * Fetch all installed plugins.
 * @returns Array of plugin metadata objects
 */
export async function getPlugins(): Promise<Plugin[]> {
  const response = await fetch(`${API_BASE}/plugins`);
  const body = await handleResponse<{ plugins: Plugin[] }>(response);
  return body.plugins;
}

/**
 * Enable or disable a plugin.
 * @param name - The plugin name
 * @param enabled - Whether to enable or disable the plugin
 * @returns The updated plugin object
 */
export async function togglePlugin(name: string, enabled: boolean): Promise<Plugin> {
  const response = await fetch(`${API_BASE}/plugins/${name}/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  return handleResponse<Plugin>(response);
}

/**
 * Fetch the configuration schema and current values for a plugin.
 * @param id - The plugin identifier
 * @returns Plugin config with schema and current values
 */
export async function getPluginConfig(id: string): Promise<PluginConfig> {
  const response = await fetch(`${API_BASE}/plugins/${id}/config`);
  return handleResponse<PluginConfig>(response);
}

/**
 * Update a plugin's configuration.
 * @param id - The plugin identifier
 * @param config - Key-value pairs of configuration to update
 * @returns The updated plugin name and config
 */
export async function updatePluginConfig(
  id: string,
  config: Record<string, unknown>,
): Promise<{ name: string; config: Record<string, unknown> }> {
  const response = await fetch(`${API_BASE}/plugins/${id}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config }),
  });
  return handleResponse<{ name: string; config: Record<string, unknown> }>(response);
}

/**
 * Fetch all available knowledge packs.
 * @returns Array of knowledge pack objects
 */
export async function getPacks(): Promise<Pack[]> {
  const response = await fetch(`${API_BASE}/packs`);
  const body = await handleResponse<{ packs: Pack[] }>(response);
  return body.packs;
}

/**
 * Install a knowledge pack by name.
 * @param name - The pack name to install
 * @returns The updated pack object
 */
export async function installPack(name: string): Promise<Pack> {
  const response = await fetch(`${API_BASE}/packs/${name}/install`, {
    method: 'POST',
  });
  return handleResponse<Pack>(response);
}

/**
 * Uninstall a knowledge pack by name.
 * @param name - The pack name to uninstall
 * @returns Confirmation with pack name and uninstall status
 */
export async function uninstallPack(name: string): Promise<{ name: string; uninstalled: boolean }> {
  const response = await fetch(`${API_BASE}/packs/${name}/uninstall`, {
    method: 'POST',
  });
  return handleResponse<{ name: string; uninstalled: boolean }>(response);
}

/**
 * Fetch suggested queries for a knowledge pack.
 * @param packId - The pack identifier
 * @returns Object containing the pack ID and its suggested queries
 */
export async function getPackSuggestedQueries(
  packId: string,
): Promise<{ packId: string; suggestedQueries: string[] }> {
  const response = await fetch(`${API_BASE}/packs/${packId}/suggested-queries`);
  return handleResponse<{ packId: string; suggestedQueries: string[] }>(response);
}

export { ApiError };
