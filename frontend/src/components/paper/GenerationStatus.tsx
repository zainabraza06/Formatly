import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

// Cycled while the model works, so the wait reads as progress rather than a hang.
const STEPS = [
  'Reading your material',
  'Identifying the key points',
  'Planning the sections',
  'Looking for charts in the data',
  'Writing the document',
  'Formatting and finishing',
]

export function GenerationStatus({
  state,
  error,
  onRetry,
  onStop,
}: {
  state: 'generating' | 'error' | null
  error?: string | null
  onRetry?: () => void
  onStop?: () => void
}) {
  const [step, setStep] = useState(0)
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (state !== 'generating') return
    setStep(0)
    setSeconds(0)
    const s = setInterval(() => setStep((i) => (i + 1) % STEPS.length), 2600)
    const t = setInterval(() => setSeconds((n) => n + 1), 1000)
    return () => {
      clearInterval(s)
      clearInterval(t)
    }
  }, [state])

  if (state === 'error') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl border border-danger/30 bg-danger/5 p-4"
      >
        <div className="flex items-center gap-2 text-sm font-medium text-danger">
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9a1 1 0 012 0v4a1 1 0 11-2 0V9zm1-4a1 1 0 100 2 1 1 0 000-2z" clipRule="evenodd" />
          </svg>
          Generation failed
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-muted">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-2"
          >
            Try again
          </button>
        )}
      </motion.div>
    )
  }

  if (state !== 'generating') return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-line bg-surface p-5"
    >
      <div className="flex items-center gap-3">
        <span className="relative flex h-8 w-8 shrink-0 items-center justify-center">
          <span className="absolute inset-0 rounded-full border-2 border-line" />
          <motion.span
            className="absolute inset-0 rounded-full border-2 border-transparent border-t-ink"
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 0.9, ease: 'linear' }}
          />
        </span>
        <div>
          <div className="text-sm font-medium text-ink">Writing your document</div>
          <div className="text-xs text-faint tabular-nums">{seconds}s elapsed</div>
        </div>
      </div>

      <div className="mt-4 h-4 overflow-hidden">
        <motion.div
          key={step}
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -10, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="text-xs text-muted"
        >
          {STEPS[step]}…
        </motion.div>
      </div>

      {/* indeterminate shimmer bar */}
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface-2">
        <motion.div
          className="h-full w-1/3 rounded-full bg-ink/40"
          animate={{ x: ['-100%', '300%'] }}
          transition={{ repeat: Infinity, duration: 1.4, ease: 'easeInOut' }}
        />
      </div>

      {/* Offered here as well as in the form: this panel is what the user is
          watching while they wait, and a long run needs a visible way out. */}
      {onStop && (
        <button
          onClick={onStop}
          className="mt-3 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-surface-2 hover:text-ink"
        >
          Stop
        </button>
      )}

    </motion.div>
  )
}
