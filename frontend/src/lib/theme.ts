export type ThemeMode = 'light' | 'dark'

const KEY = 'docpilot.theme'

export function getInitialTheme(): ThemeMode {
  const stored = localStorage.getItem(KEY)
  if (stored === 'light' || stored === 'dark') return stored
  // Light by default — it matches the white "paper" of the document canvas.
  return 'light'
}

export function applyTheme(mode: ThemeMode) {
  const root = document.documentElement
  if (mode === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
  localStorage.setItem(KEY, mode)
}
