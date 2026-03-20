import { Section, SelectField, TextField } from './FormFields';
import type { Settings } from '@/types';

const EMBEDDING_PROVIDERS = ['openai', 'ollama', 'cloudflare'] as const;

const OPENAI_EMBEDDING_MODELS = [
  'text-embedding-3-small',
  'text-embedding-3-large',
  'text-embedding-ada-002',
] as const;

const OLLAMA_EMBEDDING_MODELS_FALLBACK = [
  'nomic-embed-text',
  'mxbai-embed-large',
  'all-minilm',
] as const;

const CLOUDFLARE_EMBEDDING_MODELS = [
  '@cf/baai/bge-base-en-v1.5',
  '@cf/baai/bge-large-en-v1.5',
  '@cf/baai/bge-small-en-v1.5',
] as const;

/** Props for the EmbeddingSection component. */
interface EmbeddingSectionProps {
  form: Partial<Settings>;
  ollamaEmbeddingModels: string[];
  ollamaEmbeddingError: string | null;
  loadingEmbeddingModels: boolean;
  onFieldChange: (field: keyof Settings, value: string | number) => void;
  onRefreshEmbeddingModels: () => void;
}

/** Settings section for embedding provider and model selection. */
export function EmbeddingSection({
  form,
  ollamaEmbeddingModels,
  ollamaEmbeddingError,
  loadingEmbeddingModels,
  onFieldChange,
  onRefreshEmbeddingModels,
}: EmbeddingSectionProps) {
  return (
    <Section title="Embedding Configuration">
      <SelectField
        label="Embedding Provider"
        value={form.embeddingProvider ?? ''}
        options={EMBEDDING_PROVIDERS}
        onChange={(v) => onFieldChange('embeddingProvider', v)}
      />
      {form.embeddingProvider === 'openai' ? (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Embedding Model
          </label>
          <select
            value={form.embeddingModel ?? ''}
            onChange={(e) => onFieldChange('embeddingModel', e.target.value)}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {form.embeddingModel && !OPENAI_EMBEDDING_MODELS.includes(form.embeddingModel as typeof OPENAI_EMBEDDING_MODELS[number]) && (
              <option value={form.embeddingModel}>{form.embeddingModel}</option>
            )}
            {OPENAI_EMBEDDING_MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
      ) : form.embeddingProvider === 'ollama' ? (
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Embedding Model
            </label>
            <button
              type="button"
              onClick={onRefreshEmbeddingModels}
              disabled={loadingEmbeddingModels}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
            >
              {loadingEmbeddingModels ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
          {ollamaEmbeddingModels.length > 0 && !ollamaEmbeddingError ? (
            <select
              value={form.embeddingModel ?? ''}
              onChange={(e) => onFieldChange('embeddingModel', e.target.value)}
              className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {form.embeddingModel && !ollamaEmbeddingModels.includes(form.embeddingModel) && (
                <option value={form.embeddingModel}>{form.embeddingModel}</option>
              )}
              {ollamaEmbeddingModels.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          ) : (
            <>
              <select
                value={form.embeddingModel ?? ''}
                onChange={(e) => onFieldChange('embeddingModel', e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {form.embeddingModel && !OLLAMA_EMBEDDING_MODELS_FALLBACK.includes(form.embeddingModel as typeof OLLAMA_EMBEDDING_MODELS_FALLBACK[number]) && (
                  <option value={form.embeddingModel}>{form.embeddingModel}</option>
                )}
                {OLLAMA_EMBEDDING_MODELS_FALLBACK.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              {ollamaEmbeddingError && (
                <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                  {ollamaEmbeddingError} — showing common models as fallback.
                </p>
              )}
            </>
          )}
        </div>
      ) : form.embeddingProvider === 'cloudflare' ? (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Embedding Model
          </label>
          <select
            value={form.embeddingModel ?? ''}
            onChange={(e) => onFieldChange('embeddingModel', e.target.value)}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {form.embeddingModel && !CLOUDFLARE_EMBEDDING_MODELS.includes(form.embeddingModel as typeof CLOUDFLARE_EMBEDDING_MODELS[number]) && (
              <option value={form.embeddingModel}>{form.embeddingModel}</option>
            )}
            {CLOUDFLARE_EMBEDDING_MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
      ) : (
        <TextField
          label="Embedding Model"
          value={form.embeddingModel ?? ''}
          onChange={(v) => onFieldChange('embeddingModel', v)}
        />
      )}
    </Section>
  );
}
