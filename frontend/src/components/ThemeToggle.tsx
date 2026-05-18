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
      whileTap={{ scale: 0.98 }}
      onClick={onToggle}
      className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-medium text-neutral-900 backdrop-blur-md transition hover:bg-white/15 dark:text-neutral-100"
      aria-label="Toggle theme"
    >
      {mode === 'dark' ? 'Dark' : 'Light'}
    </motion.button>
  )
}
