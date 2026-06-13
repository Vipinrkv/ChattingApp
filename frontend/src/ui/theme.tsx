import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import '../styles/theme.css';

export type Theme = 'light' | 'dark';
export type ThemePreference = Theme | 'system';
export type AccentColor = 'blue' | 'green' | 'orange' | 'red' | 'purple' | 'pink';

export interface ColorPreset {
  primary: string;
  accent: string;
  strong: string;
  soft: string;
  ring: string;
}

export const COLOR_PRESETS: Record<Theme, Record<AccentColor, ColorPreset>> = {
  light: {
    blue: { primary: '#2563eb', accent: '#1d4ed8', strong: '#60a5fa', soft: 'rgba(59, 130, 246, 0.12)', ring: 'rgba(59, 130, 246, 0.24)' },
    green: { primary: '#10b981', accent: '#047857', strong: '#34d399', soft: 'rgba(16, 185, 129, 0.12)', ring: 'rgba(16, 185, 129, 0.24)' },
    orange: { primary: '#f97316', accent: '#c2410c', strong: '#fb923c', soft: 'rgba(249, 115, 22, 0.12)', ring: 'rgba(249, 115, 22, 0.24)' },
    red: { primary: '#ef4444', accent: '#b91c1c', strong: '#f87171', soft: 'rgba(239, 68, 68, 0.12)', ring: 'rgba(239, 68, 68, 0.24)' },
    purple: { primary: '#8b5cf6', accent: '#6d28d9', strong: '#a78bfa', soft: 'rgba(139, 92, 246, 0.12)', ring: 'rgba(139, 92, 246, 0.24)' },
    pink: { primary: '#ec4899', accent: '#be185d', strong: '#f472b6', soft: 'rgba(236, 72, 153, 0.12)', ring: 'rgba(236, 72, 153, 0.24)' },
  },
  dark: {
    blue: { primary: '#60a5fa', accent: '#3b82f6', strong: '#93c5fd', soft: 'rgba(59, 130, 246, 0.16)', ring: 'rgba(96, 165, 250, 0.28)' },
    green: { primary: '#34d399', accent: '#10b981', strong: '#6ee7b7', soft: 'rgba(16, 185, 129, 0.16)', ring: 'rgba(52, 211, 153, 0.28)' },
    orange: { primary: '#fb923c', accent: '#f97316', strong: '#fdba74', soft: 'rgba(249, 115, 22, 0.16)', ring: 'rgba(251, 146, 60, 0.28)' },
    red: { primary: '#f87171', accent: '#ef4444', strong: '#fca5a5', soft: 'rgba(239, 68, 68, 0.16)', ring: 'rgba(248, 113, 113, 0.28)' },
    purple: { primary: '#a78bfa', accent: '#8b5cf6', strong: '#c4b5fd', soft: 'rgba(139, 92, 246, 0.16)', ring: 'rgba(167, 139, 250, 0.28)' },
    pink: { primary: '#f472b6', accent: '#ec4899', strong: '#f9a8d4', soft: 'rgba(236, 72, 153, 0.16)', ring: 'rgba(244, 114, 182, 0.28)' },
  }
};

const THEME_STORAGE_KEY = 'chattingapp_theme';
const ACCENT_STORAGE_KEY = 'chattingapp_accent';

const ThemeContext = createContext({
  theme: 'light' as Theme,
  preference: 'system' as ThemePreference,
  accentColor: 'blue' as AccentColor,
  toggle: () => {},
  setTheme: (_t: ThemePreference) => {},
  setAccentColor: (_c: AccentColor) => {},
});

function getSystemTheme(): Theme {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function readStoredTheme(): ThemePreference {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY) as ThemePreference | null;
    return value === 'light' || value === 'dark' || value === 'system' ? value : 'system';
  } catch {
    return 'system';
  }
}

function readStoredAccent(): AccentColor {
  try {
    const value = localStorage.getItem(ACCENT_STORAGE_KEY) as AccentColor | null;
    return ['blue', 'green', 'orange', 'red', 'purple', 'pink'].includes(value || '') ? (value as AccentColor) : 'blue';
  } catch {
    return 'blue';
  }
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [preference, setPreference] = useState<ThemePreference>(() => readStoredTheme());
  const [systemTheme, setSystemTheme] = useState<Theme>(() => getSystemTheme());
  const [accentColor, setAccentColorState] = useState<AccentColor>(() => readStoredAccent());

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
    try { localStorage.setItem(THEME_STORAGE_KEY, preference); } catch {}
  }, [theme, preference]);

  useEffect(() => {
    const root = document.documentElement;
    const presets = COLOR_PRESETS[theme][accentColor];
    if (presets) {
      root.style.setProperty('--color-primary', presets.primary);
      root.style.setProperty('--color-accent', presets.accent);
      root.style.setProperty('--accent-strong', presets.strong);
      root.style.setProperty('--accent-soft', presets.soft);
      root.style.setProperty('--focus-ring', presets.ring);
    }
    try { localStorage.setItem(ACCENT_STORAGE_KEY, accentColor); } catch {}
  }, [theme, accentColor]);

  const setTheme = (next: ThemePreference) => setPreference(next);
  const toggle = () => setPreference(theme === 'dark' ? 'light' : 'dark');
  const setAccentColor = (next: AccentColor) => setAccentColorState(next);

  return (
    <ThemeContext.Provider value={{ theme, preference, accentColor, toggle, setTheme, setAccentColor }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
