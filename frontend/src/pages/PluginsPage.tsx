import { useState, useEffect, useCallback } from 'react';
import { getPlugins, getPluginConfig, updatePluginConfig, togglePlugin } from '@/lib/api';
import type { Plugin, PluginConfigField } from '@/types';

interface ExpandedConfig {
  config: Record<string, unknown>;
  schema: PluginConfigField[];
  saving: boolean;
}

export function PluginsPage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPlugin, setExpandedPlugin] = useState<string | null>(null);
  const [configData, setConfigData] = useState<Record<string, ExpandedConfig>>({});

  const fetchPlugins = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getPlugins();
      setPlugins(data);
    } catch {
      setError('Could not load plugins.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlugins();
  }, [fetchPlugins]);

  const handleToggle = useCallback(async (name: string, currentEnabled: boolean) => {
    try {
      await togglePlugin(name, !currentEnabled);
      setPlugins((prev) =>
        prev.map((p) => (p.name === name ? { ...p, enabled: !currentEnabled } : p)),
      );
    } catch {
      // ignore
    }
  }, []);

  const handleSettingsToggle = useCallback(async (pluginId: string) => {
    if (expandedPlugin === pluginId) {
      setExpandedPlugin(null);
      return;
    }
    setExpandedPlugin(pluginId);
    if (!configData[pluginId]) {
      try {
        const data = await getPluginConfig(pluginId);
        setConfigData((prev) => ({
          ...prev,
          [pluginId]: {
            config: data.config,
            schema: data.configSchema,
            saving: false,
          },
        }));
      } catch {
        // ignore
      }
    }
  }, [expandedPlugin, configData]);

  const handleConfigChange = useCallback((pluginId: string, fieldName: string, value: unknown) => {
    setConfigData((prev) => {
      const existing = prev[pluginId];
      if (!existing) return prev;
      return {
        ...prev,
        [pluginId]: {
          ...existing,
          config: { ...existing.config, [fieldName]: value },
        },
      };
    });
  }, []);

  const handleConfigSave = useCallback(async (pluginId: string) => {
    const existing = configData[pluginId];
    if (!existing) return;
    setConfigData((prev) => ({
      ...prev,
      [pluginId]: { ...existing, saving: true },
    }));
    try {
      const result = await updatePluginConfig(pluginId, existing.config);
      setConfigData((prev) => ({
        ...prev,
        [pluginId]: { ...prev[pluginId], config: result.config, saving: false },
      }));
    } catch {
      setConfigData((prev) => ({
        ...prev,
        [pluginId]: { ...prev[pluginId], saving: false },
      }));
    }
  }, [configData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading plugins…</p>
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

  if (plugins.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">No plugins installed.</p>
      </div>
    );
  }

  const inputCls =
    'block w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors';

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Plugins
        </h1>
      </header>

      <ul className="divide-y divide-gray-200 dark:divide-white/10 border-t border-gray-200 dark:border-white/10">
        {plugins.map((plugin) => {
          const hasConfig = plugin.configSchema && plugin.configSchema.length > 0;
          const isExpanded = expandedPlugin === plugin.name;
          const pluginConfig = configData[plugin.name];

          return (
            <li key={plugin.name} className="py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {plugin.name}
                    </h3>
                    <span className="text-xs font-mono text-gray-400 dark:text-gray-500">
                      v{plugin.version}
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
                    {plugin.description}
                  </p>
                </div>

                <div className="flex items-center gap-4 shrink-0 pt-0.5">
                  {hasConfig && (
                    <button
                      onClick={() => handleSettingsToggle(plugin.name)}
                      aria-label={`Settings for ${plugin.name}`}
                      className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                    >
                      {isExpanded ? 'Hide' : 'Settings'}
                    </button>
                  )}
                  <button
                    onClick={() => handleToggle(plugin.name, plugin.enabled)}
                    aria-label={`Toggle ${plugin.name}`}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                      plugin.enabled
                        ? 'bg-gray-900 dark:bg-white'
                        : 'bg-gray-200 dark:bg-white/20'
                    }`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-full transition-transform ${
                        plugin.enabled
                          ? 'translate-x-[18px] bg-white dark:bg-gray-900'
                          : 'translate-x-[3px] bg-white dark:bg-gray-300'
                      }`}
                    />
                  </button>
                </div>
              </div>

              {hasConfig && isExpanded && pluginConfig && (
                <div className="mt-4 pt-4 border-t border-dashed border-gray-200 dark:border-white/10 space-y-4">
                  {pluginConfig.schema.map((field) => (
                    <div key={field.name}>
                      <label
                        htmlFor={`${plugin.name}-${field.name}`}
                        className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5"
                      >
                        {field.label || field.name}
                      </label>
                      {field.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1.5">
                          {field.description}
                        </p>
                      )}
                      {field.fieldType === 'boolean' ? (
                        <input
                          id={`${plugin.name}-${field.name}`}
                          type="checkbox"
                          checked={!!pluginConfig.config[field.name]}
                          onChange={(e) =>
                            handleConfigChange(plugin.name, field.name, e.target.checked)
                          }
                          className="h-4 w-4 accent-gray-900 dark:accent-white"
                        />
                      ) : field.fieldType === 'select' && field.options ? (
                        <select
                          id={`${plugin.name}-${field.name}`}
                          value={String(pluginConfig.config[field.name] ?? '')}
                          onChange={(e) =>
                            handleConfigChange(plugin.name, field.name, e.target.value)
                          }
                          className={inputCls}
                        >
                          {field.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : field.fieldType === 'number' ? (
                        <input
                          id={`${plugin.name}-${field.name}`}
                          type="number"
                          value={String(pluginConfig.config[field.name] ?? '')}
                          onChange={(e) =>
                            handleConfigChange(plugin.name, field.name, parseFloat(e.target.value) || 0)
                          }
                          className={inputCls}
                        />
                      ) : (
                        <input
                          id={`${plugin.name}-${field.name}`}
                          type="text"
                          value={String(pluginConfig.config[field.name] ?? '')}
                          onChange={(e) =>
                            handleConfigChange(plugin.name, field.name, e.target.value)
                          }
                          className={inputCls}
                        />
                      )}
                    </div>
                  ))}
                  <div>
                    <button
                      onClick={() => handleConfigSave(plugin.name)}
                      disabled={pluginConfig.saving}
                      className="rounded-full px-4 py-2 text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 disabled:opacity-40 transition-opacity"
                    >
                      {pluginConfig.saving ? 'Saving…' : 'Save'}
                    </button>
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
