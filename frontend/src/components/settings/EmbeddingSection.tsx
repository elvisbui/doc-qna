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

interface EmbeddingSectionProps {
  form: Partial<Settings>;
  ollamaEmbeddingModels: string[];
  ollamaEmbeddingError: string | null;
  loadingEmbeddingModels: boolean;
  onFieldChange: (field: keyof Settings, value: string | number) => void;
  onRefreshEmbeddingModels: () => void;
}

export function EmbeddingSection({
  form,
  ollamaEmbeddingModels,
  ollamaEmbeddingError,
  loadingEmbeddingModels,
  onFieldChange,
  onRefreshEmbeddingModels,
}: EmbeddingSectionProps) {
  const inputCls =
    'w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors';

  return (
    <Section title="Embeddings">
      <SelectField
        label="Provider"
        value={form.embeddingProvider ?? ''}
        options={EMBEDDING_PROVIDERS}
        onChange={(v) => onFieldChange('embeddingProvider', v)}
      />
      {form.embeddingProvider === 'openai' ? (
        <div>
          <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
            Model
          </label>
          <select
            value={form.embeddingModel ?? ''}
            onChange={(e) => onFieldChange('embeddingModel', e.target.value)}
            className={inputCls}
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
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Model
            </label>
            <button
              type="button"
              onClick={onRefreshEmbeddingModels}
              disabled={loadingEmbeddingModels}
              className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-40 transition-colors"
            >
              {loadingEmbeddingModels ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
          {ollamaEmbeddingModels.length > 0 && !ollamaEmbeddingError ? (
            <select
              value={form.embeddingModel ?? ''}
              onChange={(e) => onFieldChange('embeddingModel', e.target.value)}
              className={inputCls}
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
                className={inputCls}
              >
                {form.embeddingModel && !OLLAMA_EMBEDDING_MODELS_FALLBACK.includes(form.embeddingModel as typeof OLLAMA_EMBEDDING_MODELS_FALLBACK[number]) && (
                  <option value={form.embeddingModel}>{form.embeddingModel}</option>
                )}
                {OLLAMA_EMBEDDING_MODELS_FALLBACK.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              {ollamaEmbeddingError && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                  {ollamaEmbeddingError} Showing common models.
                </p>
              )}
            </>
          )}
        </div>
      ) : form.embeddingProvider === 'cloudflare' ? (
        <div>
          <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
            Model
          </label>
          <select
            value={form.embeddingModel ?? ''}
            onChange={(e) => onFieldChange('embeddingModel', e.target.value)}
            className={inputCls}
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
          label="Model"
          value={form.embeddingModel ?? ''}
          onChange={(v) => onFieldChange('embeddingModel', v)}
        />
      )}
    </Section>
  );
}
