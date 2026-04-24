import { useState, useEffect } from 'react';
import { getPresets } from '@/lib/api';
import type { PromptPreset } from '@/lib/api';
import { Section } from './FormFields';
import type { Settings } from '@/types';

const DEFAULT_SYSTEM_PROMPT =
  "Use the following context to answer the question. " +
  "If the context does not contain enough information, say so.\n\n" +
  "Context:\n{context}";

interface SystemPromptSectionProps {
  form: Partial<Settings>;
  settings: Settings | null;
  onFieldChange: (field: keyof Settings, value: string | number) => void;
}

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

  const inputCls =
    'w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors';

  return (
    <Section title="System prompt">
      <div>
        <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
          Preset
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
          className={inputCls}
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
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Prompt
          </label>
          <button
            type="button"
            onClick={() => onFieldChange('systemPrompt', DEFAULT_SYSTEM_PROMPT)}
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
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
          className={`${inputCls} font-mono leading-relaxed`}
        />
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
          Use <code className="bg-gray-100 dark:bg-white/10 px-1 rounded">{'{context}'}</code> where retrieved chunks should be inserted. Empty falls back to the default.
        </p>
      </div>
    </Section>
  );
}
