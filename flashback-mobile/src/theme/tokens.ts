// Tokens de design Flashback Restore — version mobile
// Cohérent avec le thème dark du site web

export const darkTheme = {
  colors: {
    // Backgrounds
    background: '#0a0a0a',
    surface: '#1c1917',
    card: '#292524',

    // Texte
    foreground: '#f1f5f9',
    muted: '#a8a29e',

    // Accent (orange/ambre — comme le site)
    accent: '#f59e0b',
    accentForeground: '#0a0a0a',

    // Statuts
    success: '#22c55e',
    error: '#ef4444',
    warning: '#eab308',

    // Bordures
    border: '#374151',

    // Inputs
    input: '#292524',
    inputForeground: '#f1f5f9',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  radii: {
    sm: 8,
    md: 12,
    lg: 16,
    full: 9999,
  },
} as const
