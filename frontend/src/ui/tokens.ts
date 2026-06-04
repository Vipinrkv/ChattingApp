// Design tokens used across the app
export const tokens = {
  colors: {
    primary: 'var(--color-primary)',
    accent: 'var(--accent)',
    accentStrong: 'var(--accent-strong)',
    accentSoft: 'var(--accent-soft)',
    background: 'var(--bg)',
    surface: 'var(--surface)',
    surfaceSoft: 'var(--surface-soft)',
    surfaceStrong: 'var(--surface-strong)',
    text: 'var(--text)',
    muted: 'var(--muted)',
    border: 'var(--border)',
    success: 'var(--success)',
    danger: 'var(--danger)',
    warning: 'var(--warning)',
  },
  spacing: {
    '2xs': 'var(--space-2xs)',
    xs: 'var(--space-xs)',
    sm: 'var(--space-sm)',
    md: 'var(--space-md)',
    lg: 'var(--space-lg)',
    xl: 'var(--space-xl)',
    '2xl': 'var(--space-2xl)',
  },
  radii: {
    sm: 'var(--radius-sm)',
    md: 'var(--radius-md)',
    lg: 'var(--radius-lg)',
    pill: 'var(--radius-pill)',
  },
  typography: {
    fontSans: 'var(--font-sans)',
    textXs: 'var(--text-xs)',
    textSm: 'var(--text-sm)',
    textMd: 'var(--text-md)',
    textLg: 'var(--text-lg)',
    textXl: 'var(--text-xl)',
    heading: 'var(--font-heading)',
    lineTight: 'var(--line-tight)',
    lineNormal: 'var(--line-normal)',
  },
  shadows: {
    surface: 'var(--shadow)',
    soft: 'var(--shadow-soft)',
  },
  sizes: {
    avatar: '40px',
    controlHeight: '40px',
    touchTarget: '44px',
  },
};

export type Tokens = typeof tokens;
