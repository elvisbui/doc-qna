import { useState, useCallback } from 'react';
import { saveApiKeys } from '@/lib/api';
import { Section, KeyStatus } from './FormFields';
import type { Settings } from '@/types';
import type { ToastType } from '@/hooks/useToast';

/** Props for the ApiKeysSection component. */
interface ApiKeysSectionProps {
  settings: Settings | null;
  addToast: (type: ToastType, message: string) => string;
  onRefresh: () => Promise<void>;
}

/** Settings section for entering and saving API keys for OpenAI, Anthropic, and Cloudflare. */
export function ApiKeysSection({ settings, addToast, onRefresh }: ApiKeysSectionProps) {
  const [openaiKeyInput, setOpenaiKeyInput] = useState('');
  const [anthropicKeyInput, setAnthropicKeyInput] = useState('');
  const [cloudflareTokenInput, setCloudflareTokenInput] = useState('');
  const [cloudflareAccountIdInput, setCloudflareAccountIdInput] = useState('');
  const [savingKeys, setSavingKeys] = useState(false);

  const handleSaveKeys = useCallback(async () => {
    const keys: Record<string, string> = {};
    if (openaiKeyInput.trim()) keys.openaiApiKey = openaiKeyInput.trim();
    if (anthropicKeyInput.trim()) keys.anthropicApiKey = anthropicKeyInput.trim();
    if (cloudflareTokenInput.trim()) keys.cloudflareApiToken = cloudflareTokenInput.trim();
    if (cloudflareAccountIdInput.trim()) keys.cloudflareAccountId = cloudflareAccountIdInput.trim();

    if (Object.keys(keys).length === 0) {
      addToast('error', 'Enter at least one API key to save.');
      return;
    }

    setSavingKeys(true);
    try {
      await saveApiKeys(keys);
      addToast('success', 'API keys saved successfully.');
      setOpenaiKeyInput('');
      setAnthropicKeyInput('');
      setCloudflareTokenInput('');
      setCloudflareAccountIdInput('');
      await onRefresh();
    } catch {
      addToast('error', 'Failed to save API keys.');
    } finally {
      setSavingKeys(false);
    }
  }, [openaiKeyInput, anthropicKeyInput, cloudflareTokenInput, cloudflareAccountIdInput, addToast, onRefresh]);

  const hasInput = !!(openaiKeyInput.trim() || anthropicKeyInput.trim() || cloudflareTokenInput.trim() || cloudflareAccountIdInput.trim());

  return (
    <Section title="API Keys">
      <div className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              OpenAI API Key
            </label>
            <KeyStatus label="" present={settings?.hasOpenaiKey ?? false} />
          </div>
          <input
            type="password"
            data-testid="openai-key-input"
            value={openaiKeyInput}
            onChange={(e) => setOpenaiKeyInput(e.target.value)}
            placeholder={settings?.hasOpenaiKey ? `Current: ${settings.openaiKeyHint}` : 'sk-...'}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Anthropic API Key
            </label>
            <KeyStatus label="" present={settings?.hasAnthropicKey ?? false} />
          </div>
          <input
            type="password"
            data-testid="anthropic-key-input"
            value={anthropicKeyInput}
            onChange={(e) => setAnthropicKeyInput(e.target.value)}
            placeholder={settings?.hasAnthropicKey ? `Current: ${settings.anthropicKeyHint}` : 'sk-ant-...'}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Cloudflare Account ID
          </label>
          <input
            type="text"
            data-testid="cloudflare-account-id-input"
            value={cloudflareAccountIdInput}
            onChange={(e) => setCloudflareAccountIdInput(e.target.value)}
            placeholder="Cloudflare Account ID"
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Cloudflare API Token
            </label>
            <KeyStatus label="" present={settings?.hasCloudflareToken ?? false} />
          </div>
          <input
            type="password"
            data-testid="cloudflare-token-input"
            value={cloudflareTokenInput}
            onChange={(e) => setCloudflareTokenInput(e.target.value)}
            placeholder={settings?.hasCloudflareToken ? `Current: ${settings.cloudflareKeyHint}` : 'Cloudflare API Token'}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
        Keys are stored in the settings overlay file. They are never exposed via the API.
      </p>
      <div className="pt-2">
        <button
          onClick={handleSaveKeys}
          disabled={savingKeys || !hasInput}
          className="px-6 py-2 bg-green-600 text-white rounded-md font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {savingKeys ? 'Saving...' : 'Save Keys'}
        </button>
      </div>
    </Section>
  );
}
