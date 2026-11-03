import { createContext, useContext, useEffect, useState } from 'react'

const ThemeCtx = createContext({ theme: 'dark', toggle: () => {} })

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') || 'dark')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try { localStorage.setItem('mb-theme', theme) } catch { /* ignore */ }
  }, [theme])
  return <ThemeCtx.Provider value={{ theme, toggle: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')) }}>{children}</ThemeCtx.Provider>
}

export const useTheme = () => useContext(ThemeCtx)

/** Read chart colours from the active theme so Recharts follows dark/light. */
export function useChartColors() {
  const { theme } = useTheme()
  const css = getComputedStyle(document.documentElement)
  const v = (n) => `rgb(${css.getPropertyValue(`--${n}`).trim().replace(/ /g, ',')})`
  return {
    accent: v('accent'), sky: v('sky'), amber: v('amber'), rose: v('rose'), violet: v('violet'), mute: v('mute'),
    line: v('line'), surface: v('surface'), ink: v('ink'), theme,
  }
}
