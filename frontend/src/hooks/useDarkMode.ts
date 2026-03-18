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

function resolveIsDark(theme: Theme): boolean {
  if (theme === 'system') return getSystemPreference();
  return theme === 'dark';
}

export function useDarkMode() {
  const [theme, setTheme] = useState<Theme>(getStoredTheme);

  useEffect(() => {
    const isDark = resolveIsDark(theme);
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

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
