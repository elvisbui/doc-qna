import { useState, useCallback } from 'react';
import { saveApiKeys } from '@/lib/api';
import { Section, KeyStatus } from './FormFields';
import type { Settings } from '@/types';
import type { ToastType } from '@/hooks/useToast';

interface ApiKeysSectionProps {
  settings: Settings | null;
  addToast: (type: ToastType, message: string) => string;
  onRefresh: () => Promise<void>;
}

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
      addToast('error', 'Enter at least one key.');
      return;
    }

    setSavingKeys(true);
    try {
      await saveApiKeys(keys);
      addToast('success', 'Keys saved.');
      setOpenaiKeyInput('');
      setAnthropicKeyInput('');
      setCloudflareTokenInput('');
      setCloudflareAccountIdInput('');
      await onRefresh();
    } catch {
      addToast('error', 'Could not save keys.');
    } finally {
      setSavingKeys(false);
    }
  }, [openaiKeyInput, anthropicKeyInput, cloudflareTokenInput, cloudflareAccountIdInput, addToast, onRefresh]);

  const hasInput = !!(openaiKeyInput.trim() || anthropicKeyInput.trim() || cloudflareTokenInput.trim() || cloudflareAccountIdInput.trim());

  const inputCls =
    'w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors';

  return (
    <Section
      title="API keys"
      description="Keys are stored on the server and never returned to the client."
    >
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            OpenAI
          </label>
          <KeyStatus label="" present={settings?.hasOpenaiKey ?? false} />
        </div>
        <input
          type="password"
          data-testid="openai-key-input"
          value={openaiKeyInput}
          onChange={(e) => setOpenaiKeyInput(e.target.value)}
          placeholder={settings?.hasOpenaiKey ? `Current: ${settings.openaiKeyHint}` : 'sk-…'}
          className={inputCls}
        />
      </div>
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Anthropic
          </label>
          <KeyStatus label="" present={settings?.hasAnthropicKey ?? false} />
        </div>
        <input
          type="password"
          data-testid="anthropic-key-input"
          value={anthropicKeyInput}
          onChange={(e) => setAnthropicKeyInput(e.target.value)}
          placeholder={settings?.hasAnthropicKey ? `Current: ${settings.anthropicKeyHint}` : 'sk-ant-…'}
          className={inputCls}
        />
      </div>
      <div>
        <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
          Cloudflare account ID
        </label>
        <input
          type="text"
          data-testid="cloudflare-account-id-input"
          value={cloudflareAccountIdInput}
          onChange={(e) => setCloudflareAccountIdInput(e.target.value)}
          placeholder="account id"
          className={inputCls}
        />
      </div>
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Cloudflare API token
          </label>
          <KeyStatus label="" present={settings?.hasCloudflareToken ?? false} />
        </div>
        <input
          type="password"
          data-testid="cloudflare-token-input"
          value={cloudflareTokenInput}
          onChange={(e) => setCloudflareTokenInput(e.target.value)}
          placeholder={settings?.hasCloudflareToken ? `Current: ${settings.cloudflareKeyHint}` : 'token'}
          className={inputCls}
        />
      </div>
      <div className="pt-1">
        <button
          onClick={handleSaveKeys}
          disabled={savingKeys || !hasInput}
          className="rounded-full px-4 py-2 text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
        >
          {savingKeys ? 'Saving…' : 'Save keys'}
        </button>
      </div>
    </Section>
  );
}
