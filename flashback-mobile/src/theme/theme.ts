import { createContext, useContext } from 'react'

// Thème unique dark — Flashback Restore
export const theme = {
  colors: {
    background: '#0a0a0a',
    surface: '#1c1917',
    card: '#292524',
    foreground: '#f1f5f9',
    muted: '#a8a29e',
    accent: '#f59e0b',
    accentForeground: '#0a0a0a',
    success: '#22c55e',
    error: '#ef4444',
    warning: '#eab308',
    border: '#374151',
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

export type Theme = typeof theme

const ThemeContext = createContext<Theme>(theme)

export const ThemeProvider = ThemeContext.Provider
export const useTheme = () => useContext(ThemeContext)
