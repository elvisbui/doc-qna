import { useEffect, useCallback } from 'react';

/** Key combination descriptor for keyboard shortcuts. */
interface KeyCombo {
  /** The key value to match (e.g., "k", "Enter"). */
  key: string;
  /** Whether Ctrl (Windows/Linux) or Cmd (Mac) must be held. */
  ctrlOrMeta?: boolean;
  /** Whether the Shift key must be held. */
  shift?: boolean;
  /** Whether the Alt key must be held. */
  alt?: boolean;
}

/**
 * Registers a global keydown listener for a key combination.
 * `ctrlOrMeta` matches either Ctrl (Windows/Linux) or Cmd (Mac).
 * @param combo - The key combination to listen for.
 * @param callback - Function to invoke when the shortcut is triggered.
 * @param enabled - Whether the shortcut is active (defaults to true).
 */
export function useKeyboardShortcut(
  combo: KeyCombo,
  callback: () => void,
  enabled: boolean = true,
) {
  const stableCallback = useCallback(callback, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const handler = (e: KeyboardEvent) => {
      const ctrlOrMeta = combo.ctrlOrMeta
        ? e.ctrlKey || e.metaKey
        : !(e.ctrlKey || e.metaKey);
      const shift = combo.shift ? e.shiftKey : !e.shiftKey;
      const alt = combo.alt ? e.altKey : !e.altKey;

      if (e.key === combo.key && ctrlOrMeta && shift && alt) {
        e.preventDefault();
        stableCallback();
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [combo.key, combo.ctrlOrMeta, combo.shift, combo.alt, stableCallback, enabled]);
}
