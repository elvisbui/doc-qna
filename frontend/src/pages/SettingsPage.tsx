import { useState, useEffect, useCallback } from 'react';
import { useSettings } from '@/hooks/useSettings';
import { getOllamaModels, testProviderConnection } from '@/lib/api';
import type { OllamaModel, TestConnectionResult } from '@/lib/api';
import type { Settings } from '@/types';
import type { ToastType } from '@/hooks/useToast';
import { LLMSection } from '@/components/settings/LLMSection';
import { EmbeddingSection } from '@/components/settings/EmbeddingSection';
import { ApiKeysSection } from '@/components/settings/ApiKeysSection';
import { SystemPromptSection } from '@/components/settings/SystemPromptSection';
import { Section, SelectField, NumberField } from '@/components/settings/FormFields';

interface SettingsPageProps {
  addToast: (type: ToastType, message: string) => string;
}

const CHUNKING_STRATEGIES = ['fixed', 'semantic'] as const;
const RETRIEVAL_STRATEGIES = ['vector', 'hybrid'] as const;
const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR'] as const;

export function SettingsPage({ addToast }: SettingsPageProps) {
  const { settings, isLoading, error, updateSettings, refresh } = useSettings();
  const [form, setForm] = useState<Partial<Settings>>({});
  const [saving, setSaving] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [ollamaModelsError, setOllamaModelsError] = useState<string | null>(null);
  const [loadingModels, setLoadingModels] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionResult, setConnectionResult] = useState<TestConnectionResult | null>(null);
  const [ollamaEmbeddingModels, setOllamaEmbeddingModels] = useState<string[]>([]);
  const [ollamaEmbeddingError, setOllamaEmbeddingError] = useState<string | null>(null);
  const [loadingEmbeddingModels, setLoadingEmbeddingModels] = useState(false);

  const fetchOllamaModels = useCallback(async () => {
    setLoadingModels(true);
    setOllamaModelsError(null);
    try {
      const result = await getOllamaModels();
      setOllamaModels(result.models);
      if (result.error) {
        setOllamaModelsError(result.error);
      }
    } catch {
      setOllamaModelsError('Failed to fetch Ollama models');
      setOllamaModels([]);
    } finally {
      setLoadingModels(false);
    }
  }, []);

  useEffect(() => {
    if (settings) {
      setForm({
        llmProvider: settings.llmProvider,
        ollamaBaseUrl: settings.ollamaBaseUrl,
        ollamaModel: settings.ollamaModel,
        embeddingProvider: settings.embeddingProvider,
        embeddingModel: settings.embeddingModel,
        chunkingStrategy: settings.chunkingStrategy,
        retrievalStrategy: settings.retrievalStrategy,
        chunkSize: settings.chunkSize,
        chunkOverlap: settings.chunkOverlap,
        logLevel: settings.logLevel,
        systemPrompt: settings.systemPrompt,
        llmTemperature: settings.llmTemperature,
        llmTopP: settings.llmTopP,
        llmMaxTokens: settings.llmMaxTokens,
      });
    }
  }, [settings]);

  useEffect(() => {
    if (form.llmProvider === 'ollama') {
      fetchOllamaModels();
    }
  }, [form.llmProvider, fetchOllamaModels]);

  const fetchOllamaEmbeddingModels = useCallback(async () => {
    setLoadingEmbeddingModels(true);
    setOllamaEmbeddingError(null);
    try {
      const result = await getOllamaModels();
      if (result.error) {
        setOllamaEmbeddingError(result.error);
        setOllamaEmbeddingModels([]);
      } else {
        const embeddingModels = result.models.filter(
          (m) => m.name.includes('embed') || m.name.includes('minilm'),
        );
        const names = embeddingModels.length > 0
          ? embeddingModels.map((m) => m.name)
          : result.models.map((m) => m.name);
        setOllamaEmbeddingModels(names);
      }
    } catch {
      setOllamaEmbeddingError('Failed to fetch Ollama models');
      setOllamaEmbeddingModels([]);
    } finally {
      setLoadingEmbeddingModels(false);
    }
  }, []);

  useEffect(() => {
    if (form.embeddingProvider === 'ollama') {
      fetchOllamaEmbeddingModels();
    }
  }, [form.embeddingProvider, fetchOllamaEmbeddingModels]);

  const handleChange = useCallback(
    (field: keyof Settings, value: string | number) => {
      setForm((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    const ok = await updateSettings(form);
    setSaving(false);
    if (ok) {
      addToast('success', 'Settings saved.');
    } else {
      addToast('error', 'Could not save settings.');
    }
  }, [form, updateSettings, addToast]);

  const handleTestConnection = useCallback(async () => {
    const provider = form.llmProvider;
    if (!provider) return;

    setTestingConnection(true);
    setConnectionResult(null);
    try {
      const config: Record<string, string> = {};
      if (provider === 'ollama' && form.ollamaBaseUrl) {
        config.base_url = form.ollamaBaseUrl;
      }
      const result = await testProviderConnection(provider, config);
      setConnectionResult(result);
    } catch {
      setConnectionResult({ status: 'error', message: 'Could not reach the server.' });
    } finally {
      setTestingConnection(false);
    }
  }, [form.llmProvider, form.ollamaBaseUrl]);

  if (isLoading && !settings) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading settings…</p>
      </div>
    );
  }

  if (error && !settings) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-600 dark:text-gray-300">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <header className="mb-10">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Settings
        </h1>
      </header>

      <div className="space-y-10">
        <LLMSection
          form={form}
          ollamaModels={ollamaModels}
          ollamaModelsError={ollamaModelsError}
          loadingModels={loadingModels}
          testingConnection={testingConnection}
          connectionResult={connectionResult}
          onFieldChange={handleChange}
          onTestConnection={handleTestConnection}
          onRefreshModels={fetchOllamaModels}
          onClearConnectionResult={() => setConnectionResult(null)}
        />

        <EmbeddingSection
          form={form}
          ollamaEmbeddingModels={ollamaEmbeddingModels}
          ollamaEmbeddingError={ollamaEmbeddingError}
          loadingEmbeddingModels={loadingEmbeddingModels}
          onFieldChange={handleChange}
          onRefreshEmbeddingModels={fetchOllamaEmbeddingModels}
        />

        <Section title="Chunking and retrieval">
          <SelectField
            label="Chunking strategy"
            value={form.chunkingStrategy ?? ''}
            options={CHUNKING_STRATEGIES}
            onChange={(v) => handleChange('chunkingStrategy', v)}
          />
          <SelectField
            label="Retrieval strategy"
            value={form.retrievalStrategy ?? ''}
            options={RETRIEVAL_STRATEGIES}
            onChange={(v) => handleChange('retrievalStrategy', v)}
          />
          <NumberField
            label="Chunk size"
            value={form.chunkSize ?? 0}
            min={100}
            max={10000}
            onChange={(v) => handleChange('chunkSize', v)}
          />
          <NumberField
            label="Chunk overlap"
            value={form.chunkOverlap ?? 0}
            min={0}
            max={5000}
            onChange={(v) => handleChange('chunkOverlap', v)}
          />
        </Section>

        <SystemPromptSection
          form={form}
          settings={settings}
          onFieldChange={handleChange}
        />

        <Section title="Model parameters">
          <NumberField
            label="Temperature"
            value={form.llmTemperature ?? 0.7}
            min={0}
            max={2}
            step={0.1}
            onChange={(v) => handleChange('llmTemperature', v)}
          />
          <NumberField
            label="Top P"
            value={form.llmTopP ?? 1.0}
            min={0}
            max={1}
            step={0.05}
            onChange={(v) => handleChange('llmTopP', v)}
          />
          <NumberField
            label="Max tokens"
            value={form.llmMaxTokens ?? 2048}
            min={128}
            max={8192}
            step={1}
            onChange={(v) => handleChange('llmMaxTokens', v)}
          />
        </Section>

        <Section title="Logging">
          <SelectField
            label="Log level"
            value={form.logLevel ?? ''}
            options={LOG_LEVELS}
            onChange={(v) => handleChange('logLevel', v)}
          />
        </Section>

        <ApiKeysSection
          settings={settings}
          addToast={addToast}
          onRefresh={refresh}
        />

        <div className="pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-full px-4 py-2 text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
