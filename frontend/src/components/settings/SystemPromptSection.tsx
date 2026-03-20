import { useState, useEffect } from 'react';
import { getPresets } from '@/lib/api';
import type { PromptPreset } from '@/lib/api';
import { Section } from './FormFields';
import type { Settings } from '@/types';

const DEFAULT_SYSTEM_PROMPT =
  "Use the following context to answer the question. " +
  "If the context does not contain enough information, say so.\n\n" +
  "Context:\n{context}";

/** Props for the SystemPromptSection component. */
interface SystemPromptSectionProps {
  form: Partial<Settings>;
  settings: Settings | null;
  onFieldChange: (field: keyof Settings, value: string | number) => void;
}

/** Settings section with preset dropdown and editable system prompt textarea. */
export function SystemPromptSection({ form, settings, onFieldChange }: SystemPromptSectionProps) {
  const [presets, setPresets] = useState<PromptPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('custom');

  useEffect(() => {
    getPresets()
      .then((data) => setPresets(data))
      .catch(() => setPresets([]));
  }, []);

  useEffect(() => {
    if (settings && presets.length > 0) {
      const currentPrompt = form.systemPrompt ?? settings.systemPrompt ?? '';
      const matched = presets.find((p) => p.systemPrompt === currentPrompt);
      setSelectedPreset(matched ? matched.id : 'custom');
    }
  }, [settings, presets, form.systemPrompt]);

  return (
    <Section title="System Prompt">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Prompt Preset
        </label>
        <select
          data-testid="preset-select"
          value={selectedPreset}
          onChange={(e) => {
            const presetId = e.target.value;
            setSelectedPreset(presetId);
            if (presetId !== 'custom') {
              const preset = presets.find((p) => p.id === presetId);
              if (preset) {
                onFieldChange('systemPrompt', preset.systemPrompt);
              }
            }
          }}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {presets.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
          <option value="custom">Custom</option>
        </select>
      </div>
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Custom System Prompt
          </label>
          <button
            type="button"
            onClick={() => onFieldChange('systemPrompt', DEFAULT_SYSTEM_PROMPT)}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Reset to default
          </button>
        </div>
        <textarea
          data-testid="system-prompt-textarea"
          value={form.systemPrompt ?? ''}
          onChange={(e) => {
            onFieldChange('systemPrompt', e.target.value);
            setSelectedPreset('custom');
          }}
          rows={6}
          placeholder={DEFAULT_SYSTEM_PROMPT}
          className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Use <code className="bg-gray-100 dark:bg-gray-600 px-1 rounded">{'{context}'}</code> as a placeholder for retrieved document chunks. Leave empty to use the default prompt.
        </p>
      </div>
    </Section>
  );
}
