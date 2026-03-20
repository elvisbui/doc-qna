import { useState, useCallback, useEffect } from 'react';
import type { Settings } from '@/types';
import {
  getSettings as fetchSettings,
  updateSettings as putSettings,
} from '@/lib/api';

/** Return value of the useSettings hook. */
interface UseSettingsReturn {
  /** Current application settings, or null if not yet loaded. */
  settings: Settings | null;
  /** Whether settings are being fetched. */
  isLoading: boolean;
  /** Error message from the most recent failed operation, if any. */
  error: string | null;
  /** Apply partial settings updates to the backend. Returns true on success. */
  updateSettings: (updates: Partial<Settings>) => Promise<boolean>;
  /** Re-fetch settings from the API. */
  refresh: () => Promise<void>;
}

/**
 * Fetches and manages application settings with optimistic updates.
 * Automatically loads settings on mount.
 * @returns Settings state, loading/error indicators, and update/refresh methods.
 */
export function useSettings(): UseSettingsReturn {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchSettings();
      setSettings(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to fetch settings';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const updateSettings = useCallback(
    async (updates: Partial<Settings>): Promise<boolean> => {
      setError(null);
      try {
        const data = await putSettings(updates);
        setSettings(data);
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Failed to update settings';
        setError(message);
        return false;
      }
    },
    [],
  );

  return { settings, isLoading, error, updateSettings, refresh };
}
