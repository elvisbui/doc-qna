import { useState, useEffect, useCallback } from 'react';
import { getPacks, installPack, uninstallPack } from '@/lib/api';
import type { Pack } from '@/types';

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
      setError('Could not load packs.');
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
      // ignore
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
      // ignore
    } finally {
      setActionId(null);
    }
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading packs…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-600 dark:text-gray-300">{error}</p>
      </div>
    );
  }

  if (packs.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">No packs available.</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Packs
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Sets of documents you can install with one click.
        </p>
      </header>

      <ul className="divide-y divide-gray-200 dark:divide-white/10 border-t border-gray-200 dark:border-white/10">
        {packs.map((pack) => (
          <li key={pack.name} className="py-4 flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {pack.name}
                </h3>
                <span className="text-xs font-mono text-gray-400 dark:text-gray-500">
                  v{pack.version}
                </span>
              </div>
              <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                {pack.description}
              </p>
              <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">
                {pack.docCount} documents
              </p>
            </div>

            <div className="shrink-0 pt-0.5">
              {pack.installed ? (
                <button
                  onClick={() => handleUninstall(pack.name)}
                  disabled={actionId === pack.name}
                  className="rounded-full border border-gray-200 dark:border-white/15 px-3.5 py-1.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-white/5 disabled:opacity-40 transition-colors"
                >
                  {actionId === pack.name ? 'Removing…' : 'Remove'}
                </button>
              ) : (
                <button
                  onClick={() => handleInstall(pack.name)}
                  disabled={actionId === pack.name}
                  className="rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-3.5 py-1.5 text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-opacity"
                >
                  {actionId === pack.name ? 'Installing…' : 'Install'}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
