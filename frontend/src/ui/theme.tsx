import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import '../styles/theme.css';

type Theme = 'light' | 'dark';
type ThemePreference = Theme | 'system';

const STORAGE_KEY = 'chattingapp_theme';

const ThemeContext = createContext({
  theme: 'light' as Theme,
  preference: 'system' as ThemePreference,
  toggle: () => {},
  setTheme: (_t: ThemePreference) => {},
});

function getSystemTheme(): Theme {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function readStoredPreference(): ThemePreference {
  try {
    const value = localStorage.getItem(STORAGE_KEY) as ThemePreference | null;
    return value === 'light' || value === 'dark' || value === 'system' ? value : 'system';
  } catch {
    return 'system';
  }
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [preference, setPreference] = useState<ThemePreference>(() => readStoredPreference());
  const [systemTheme, setSystemTheme] = useState<Theme>(() => getSystemTheme());
  const theme = useMemo<Theme>(() => (preference === 'system' ? systemTheme : preference), [preference, systemTheme]);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: light)');
    const handleChange = () => setSystemTheme(media.matches ? 'light' : 'dark');
    handleChange();
    media.addEventListener('change', handleChange);
    return () => media.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.themePreference = preference;
    root.classList.toggle('theme-dark', theme === 'dark');
    root.classList.toggle('theme-light', theme === 'light');
    try { localStorage.setItem(STORAGE_KEY, preference); } catch {}
  }, [theme, preference]);

  const setTheme = (next: ThemePreference) => setPreference(next);
  const toggle = () => setPreference(theme === 'dark' ? 'light' : 'dark');

  return <ThemeContext.Provider value={{ theme, preference, toggle, setTheme }}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => useContext(ThemeContext);
