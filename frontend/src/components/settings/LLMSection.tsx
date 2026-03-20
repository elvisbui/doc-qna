import { Section, SelectField, TextField } from './FormFields';
import type { OllamaModel, TestConnectionResult } from '@/lib/api';
import type { Settings } from '@/types';

const LLM_PROVIDERS = ['ollama', 'openai', 'anthropic', 'cloudflare'] as const;

/** Props for the LLMSection component. */
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

/** Settings section for LLM provider selection, model picker, and connection testing. */
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
    <Section title="LLM Configuration">
      <SelectField
        label="LLM Provider"
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
          className="px-4 py-2 text-sm font-medium rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {testingConnection ? 'Testing...' : 'Test Connection'}
        </button>
        {connectionResult && (
          <span className={`flex items-center gap-1 text-sm ${connectionResult.status === 'ok' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {connectionResult.status === 'ok' ? (
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            )}
            {connectionResult.message}
          </span>
        )}
      </div>
      <TextField
        label="Ollama Base URL"
        value={form.ollamaBaseUrl ?? ''}
        onChange={(v) => onFieldChange('ollamaBaseUrl', v)}
      />
      {form.llmProvider === 'ollama' && ollamaModels.length > 0 ? (
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Ollama Model
            </label>
            <button
              type="button"
              onClick={onRefreshModels}
              disabled={loadingModels}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
            >
              {loadingModels ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
          <select
            value={form.ollamaModel ?? ''}
            onChange={(e) => onFieldChange('ollamaModel', e.target.value)}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Ollama Model
            </label>
            {form.llmProvider === 'ollama' && (
              <button
                type="button"
                onClick={onRefreshModels}
                disabled={loadingModels}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
              >
                {loadingModels ? 'Refreshing...' : 'Refresh'}
              </button>
            )}
          </div>
          <input
            type="text"
            value={form.ollamaModel ?? ''}
            onChange={(e) => onFieldChange('ollamaModel', e.target.value)}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {ollamaModelsError && form.llmProvider === 'ollama' && (
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
              {ollamaModelsError}
            </p>
          )}
        </div>
      )}
    </Section>
  );
}
