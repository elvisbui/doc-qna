import { useState } from 'react';
import type { PluginTraceEntry } from '@/types';

interface PluginActivityPanelProps {
  trace: PluginTraceEntry[];
}

export function PluginActivityPanel({ trace }: PluginActivityPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (trace.length === 0) return null;

  return (
    <div className="max-w-3xl mx-auto w-full border-t border-gray-200 dark:border-white/10">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
      >
        <span>Plugin activity ({trace.length})</span>
        <svg
          className={`h-4 w-4 text-gray-400 dark:text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {isExpanded && (
        <ul className="px-4 pb-3 pt-1 divide-y divide-gray-100 dark:divide-white/5">
          {trace.map((entry, index) => (
            <li key={index} className="flex items-center justify-between py-2 text-sm">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-gray-900 dark:text-gray-100">{entry.pluginName}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{entry.hookName}</span>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0 text-xs">
                <span className="text-gray-500 dark:text-gray-400 tabular-nums">{entry.durationMs} ms</span>
                {entry.error && (
                  <span className="text-gray-700 dark:text-gray-200">error</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
