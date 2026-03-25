import { useState, useEffect, useCallback } from 'react';

type Theme = 'light' | 'dark' | 'system';

function getSystemPreference(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function getStoredTheme(): Theme {
  const stored = localStorage.getItem('theme');
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }
  return 'system';
}

function applyDarkClass(isDark: boolean) {
  if (isDark) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

function resolveIsDark(theme: Theme): boolean {
  if (theme === 'system') return getSystemPreference();
  return theme === 'dark';
}

/**
 * Manages dark mode theme state with system preference detection and localStorage persistence.
 * Cycles through system, light, and dark themes on toggle.
 * @returns Current theme, whether dark mode is active, and a toggle function.
 */
export function useDarkMode() {
  const [theme, setTheme] = useState<Theme>(getStoredTheme);

  // Apply dark class whenever theme changes
  useEffect(() => {
    applyDarkClass(resolveIsDark(theme));
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Listen for system preference changes
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'system') {
        applyDarkClass(mq.matches);
      }
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  // Cycle: system → light → dark → system
  const toggle = useCallback(() => {
    setTheme((prev) => {
      if (prev === 'system') return 'light';
      if (prev === 'light') return 'dark';
      return 'system';
    });
  }, []);

  const isDark = resolveIsDark(theme);

  return { theme, isDark, toggle };
}
