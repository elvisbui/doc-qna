import { useState } from 'react';
import type { PluginTraceEntry } from '@/types';

/** Props for the PluginActivityPanel component. */
interface PluginActivityPanelProps {
  /** Array of plugin execution trace entries for the current response */
  trace: PluginTraceEntry[];
}

/** Collapsible panel showing plugin hook execution times and errors. */
export function PluginActivityPanel({ trace }: PluginActivityPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (trace.length === 0) return null;

  return (
    <div className="max-w-3xl mx-auto w-full border-t border-gray-100 dark:border-white/5">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
      >
        <span className="flex items-center gap-2">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 0 1-.657.643 48.39 48.39 0 0 1-4.163-.3c.186 1.613.166 3.532-.08 5.022a6.876 6.876 0 0 1 2.042-.947c.776-.253 1.467.012 1.832.582.158.248.286.512.382.793a48.036 48.036 0 0 0 4.709-.073c.096-.281.224-.545.382-.793.365-.57 1.056-.835 1.832-.582a6.876 6.876 0 0 1 2.042.947c-.246-1.49-.266-3.41-.08-5.022a48.39 48.39 0 0 1-4.163.3.64.64 0 0 1-.657-.643v0Z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 18.75c-1.5 0-3-1.5-3-3s1.5-3 3-3 3 1.5 3 3-1.5 3-3 3ZM8.25 18.75c1.5 0 3-1.5 3-3s-1.5-3-3-3-3 1.5-3 3 1.5 3 3 3Z" />
          </svg>
          Plugin Activity ({trace.length})
        </span>
        <svg
          className={`h-4 w-4 text-gray-400 dark:text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 space-y-1.5">
          {trace.map((entry, index) => (
            <div
              key={index}
              className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                entry.error
                  ? 'border-red-200 dark:border-red-800/50 bg-red-50 dark:bg-red-900/10'
                  : 'border-gray-100 dark:border-white/10 bg-gray-50/50 dark:bg-white/[0.02]'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-medium text-gray-800 dark:text-gray-200">{entry.pluginName}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{entry.hookName}</span>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-xs text-gray-500 dark:text-gray-400">{entry.durationMs} ms</span>
                {entry.error && (
                  <span className="text-xs font-medium text-red-600 dark:text-red-400">error</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
