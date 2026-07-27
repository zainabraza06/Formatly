import { motion } from 'framer-motion'

export function ThemeToggle({
  mode,
  onToggle,
}: {
  mode: 'light' | 'dark'
  onToggle: () => void
}) {
  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.96 }}
      onClick={onToggle}
      className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface text-muted transition-colors hover:bg-surface-2 hover:text-ink"
      aria-label={mode === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      title={mode === 'dark' ? 'Switch to light' : 'Switch to dark'}
    >
      {mode === 'dark' ? (
        // sun
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M10 3a1 1 0 011 1v1a1 1 0 11-2 0V4a1 1 0 011-1zm0 10a3 3 0 100-6 3 3 0 000 6zm6-3a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zm10.657-5.657a1 1 0 010 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM6.464 13.536a1 1 0 010 1.414l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 0zm0-7.072a1 1 0 01-1.414 0l-.707-.707A1 1 0 014.757 4.343l.707.707a1 1 0 010 1.414zm9.193 7.072a1 1 0 01-1.414 0l-.707-.707a1 1 0 011.414-1.414l.707.707a1 1 0 010 1.414zM10 16a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1z" />
        </svg>
      ) : (
        // moon
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
      )}
    </motion.button>
  )
}
