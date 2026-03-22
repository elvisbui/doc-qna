import { useState, useEffect, useCallback } from 'react';
import { getPlugins, getPluginConfig, updatePluginConfig, togglePlugin } from '@/lib/api';
import type { Plugin, PluginConfigField } from '@/types';

interface ExpandedConfig {
  config: Record<string, unknown>;
  schema: PluginConfigField[];
  saving: boolean;
}

/** Page for viewing, toggling, and configuring installed plugins. */
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
      setError('Failed to load plugins.');
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
      // Silently fail
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
        // Failed to load config
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
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading plugins...</p>
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

  if (plugins.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500 dark:text-gray-400">No plugins installed.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
        Plugins
      </h2>

      <div className="space-y-3">
        {plugins.map((plugin) => {
          const hasConfig = plugin.configSchema && plugin.configSchema.length > 0;
          const isExpanded = expandedPlugin === plugin.name;
          const pluginConfig = configData[plugin.name];

          return (
            <div
              key={plugin.name}
              className="rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-white/[0.03]"
            >
              <div className="p-5 flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                      {plugin.name}
                    </h3>
                    <span className="text-xs text-gray-400 dark:text-gray-500 font-mono">
                      v{plugin.version}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {plugin.description}
                  </p>
                </div>

                <div className="flex items-center gap-3 ml-4 shrink-0">
                  {hasConfig && (
                    <button
                      onClick={() => handleSettingsToggle(plugin.name)}
                      aria-label={`Settings for ${plugin.name}`}
                      className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                    >
                      Settings
                    </button>
                  )}
                  <button
                    onClick={() => handleToggle(plugin.name, plugin.enabled)}
                    aria-label={`Toggle ${plugin.name}`}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:focus:ring-offset-[#212121] ${
                      plugin.enabled
                        ? 'bg-gray-900 dark:bg-white'
                        : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full transition-transform ${
                        plugin.enabled
                          ? 'translate-x-6 bg-white dark:bg-gray-900'
                          : 'translate-x-1 bg-white dark:bg-gray-400'
                      }`}
                    />
                  </button>
                </div>
              </div>

              {hasConfig && isExpanded && pluginConfig && (
                <div className="border-t border-gray-100 dark:border-white/5 px-5 py-4">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                    Configuration
                  </h4>
                  <div className="space-y-3">
                    {pluginConfig.schema.map((field) => (
                      <div key={field.name}>
                        <label
                          htmlFor={`${plugin.name}-${field.name}`}
                          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                        >
                          {field.label || field.name}
                        </label>
                        {field.description && (
                          <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">
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
                            className="h-4 w-4 rounded border-gray-300 dark:border-gray-600"
                          />
                        ) : field.fieldType === 'select' && field.options ? (
                          <select
                            id={`${plugin.name}-${field.name}`}
                            value={String(pluginConfig.config[field.name] ?? '')}
                            onChange={(e) =>
                              handleConfigChange(plugin.name, field.name, e.target.value)
                            }
                            className="block w-full rounded-lg border border-gray-200 dark:border-white/15 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
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
                            className="block w-full rounded-lg border border-gray-200 dark:border-white/15 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
                          />
                        ) : (
                          <input
                            id={`${plugin.name}-${field.name}`}
                            type="text"
                            value={String(pluginConfig.config[field.name] ?? '')}
                            onChange={(e) =>
                              handleConfigChange(plugin.name, field.name, e.target.value)
                            }
                            className="block w-full rounded-lg border border-gray-200 dark:border-white/15 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
                          />
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="mt-4">
                    <button
                      onClick={() => handleConfigSave(plugin.name)}
                      disabled={pluginConfig.saving}
                      className="px-4 py-2 text-sm font-medium rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-80 disabled:opacity-50 transition-opacity"
                    >
                      {pluginConfig.saving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
