import { useState, useEffect, useCallback } from 'react';
import { getPacks, installPack, uninstallPack } from '@/lib/api';
import type { Pack } from '@/types';

/** Page for browsing, installing, and uninstalling knowledge packs. */
export function PacksPage() {
  const [packs, setPacks] = useState<Pack[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);

  const fetchPacks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getPacks();
      setPacks(data);
    } catch {
      setError('Failed to load packs.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPacks();
  }, [fetchPacks]);

  const handleInstall = useCallback(async (name: string) => {
    setActionId(name);
    try {
      const updated = await installPack(name);
      setPacks((prev) =>
        prev.map((p) => (p.name === name ? { ...p, ...updated, installed: true } : p)),
      );
    } catch {
      // Silently fail
    } finally {
      setActionId(null);
    }
  }, []);

  const handleUninstall = useCallback(async (name: string) => {
    setActionId(name);
    try {
      await uninstallPack(name);
      setPacks((prev) =>
        prev.map((p) => (p.name === name ? { ...p, installed: false } : p)),
      );
    } catch {
      // Silently fail
    } finally {
      setActionId(null);
    }
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading packs...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (packs.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">No knowledge packs available.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
        Knowledge Packs
      </h2>

      <div className="space-y-3">
        {packs.map((pack) => (
          <div
            key={pack.name}
            className="rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.03] p-5"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                    {pack.name}
                  </h3>
                  <span className="text-xs text-gray-400 dark:text-gray-500 font-mono">
                    v{pack.version}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {pack.description}
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  {pack.docCount} documents
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {pack.installed ? (
                  <button
                    onClick={() => handleUninstall(pack.name)}
                    disabled={actionId === pack.name}
                    className="px-4 py-1.5 text-sm font-medium rounded-full border border-gray-200 dark:border-white/15 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 hover:text-red-600 dark:hover:text-red-400 hover:border-red-200 dark:hover:border-red-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {actionId === pack.name ? 'Removing...' : 'Uninstall'}
                  </button>
                ) : (
                  <button
                    onClick={() => handleInstall(pack.name)}
                    disabled={actionId === pack.name}
                    className="px-4 py-1.5 text-sm font-medium rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
                  >
                    {actionId === pack.name ? 'Installing...' : 'Install'}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
