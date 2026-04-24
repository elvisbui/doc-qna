import { Section, SelectField, TextField } from './FormFields';
import type { OllamaModel, TestConnectionResult } from '@/lib/api';
import type { Settings } from '@/types';

const LLM_PROVIDERS = ['ollama', 'openai', 'anthropic', 'cloudflare'] as const;

interface LLMSectionProps {
  form: Partial<Settings>;
  ollamaModels: OllamaModel[];
  ollamaModelsError: string | null;
  loadingModels: boolean;
  testingConnection: boolean;
  connectionResult: TestConnectionResult | null;
  onFieldChange: (field: keyof Settings, value: string | number) => void;
  onTestConnection: () => void;
  onRefreshModels: () => void;
  onClearConnectionResult: () => void;
}

export function LLMSection({
  form,
  ollamaModels,
  ollamaModelsError,
  loadingModels,
  testingConnection,
  connectionResult,
  onFieldChange,
  onTestConnection,
  onRefreshModels,
  onClearConnectionResult,
}: LLMSectionProps) {
  return (
    <Section title="Language model">
      <SelectField
        label="Provider"
        value={form.llmProvider ?? ''}
        options={LLM_PROVIDERS}
        onChange={(v) => {
          onFieldChange('llmProvider', v);
          onClearConnectionResult();
        }}
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onTestConnection}
          disabled={testingConnection}
          className="rounded-full border border-gray-200 dark:border-white/15 px-3.5 py-1.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {testingConnection ? 'Testing…' : 'Test connection'}
        </button>
        {connectionResult && (
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {connectionResult.status === 'ok' ? 'Connected.' : connectionResult.message}
          </span>
        )}
      </div>
      <TextField
        label="Ollama base URL"
        value={form.ollamaBaseUrl ?? ''}
        onChange={(v) => onFieldChange('ollamaBaseUrl', v)}
      />
      {form.llmProvider === 'ollama' && ollamaModels.length > 0 ? (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Ollama model
            </label>
            <button
              type="button"
              onClick={onRefreshModels}
              disabled={loadingModels}
              className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-40 transition-colors"
            >
              {loadingModels ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
          <select
            value={form.ollamaModel ?? ''}
            onChange={(e) => onFieldChange('ollamaModel', e.target.value)}
            className="w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors"
          >
            {form.ollamaModel && !ollamaModels.some((m) => m.name === form.ollamaModel) && (
              <option value={form.ollamaModel}>{form.ollamaModel}</option>
            )}
            {ollamaModels.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name} ({m.size})
              </option>
            ))}
          </select>
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Ollama model
            </label>
            {form.llmProvider === 'ollama' && (
              <button
                type="button"
                onClick={onRefreshModels}
                disabled={loadingModels}
                className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 disabled:opacity-40 transition-colors"
              >
                {loadingModels ? 'Refreshing…' : 'Refresh'}
              </button>
            )}
          </div>
          <input
            type="text"
            value={form.ollamaModel ?? ''}
            onChange={(e) => onFieldChange('ollamaModel', e.target.value)}
            className="w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors"
          />
          {ollamaModelsError && form.llmProvider === 'ollama' && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
              {ollamaModelsError}
            </p>
          )}
        </div>
      )}
    </Section>
  );
}
