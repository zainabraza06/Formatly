import { useEffect, useState } from 'react'
import { Button, Progress } from '../ui'
import { WarningIcon } from '../icons'

/**
 * What is happening while the document is being written.
 *
 * The server answers once, when the whole document is finished — there is no
 * per-section event to report — so this does not pretend to a percentage. It
 * says what is being done, how long it has been going, roughly how long that
 * usually takes, and offers the way out. The elapsed count is the honest part:
 * it is the thing that proves nothing has hung.
 */
export function GenerationStatus({
  state,
  error,
  what = 'Writing your document',
  onRetry,
  onStop,
  typicalSeconds = 60,
}: {
  state: 'working' | 'error' | null
  error?: string | null
  what?: string
  onRetry?: () => void
  onStop?: () => void
  typicalSeconds?: number
}) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (state !== 'working') return
    const started = Date.now()
    const t = window.setInterval(
      () => setSeconds(Math.round((Date.now() - started) / 1000)),
      1000,
    )
    return () => window.clearInterval(t)
  }, [state])

  if (state === 'error') {
    return (
      <div role="alert" className="animate-fade-up rounded-lg border border-danger/30 bg-danger-soft/60 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-danger">
          <WarningIcon className="h-4 w-4" />
          The document could not be written
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-muted">{error}</p>
        {onRetry && (
          <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    )
  }

  if (state !== 'working') return null

  const slow = seconds > typicalSeconds * 2

  return (
    <div className="animate-fade-up rounded-lg border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">{what}…</p>
          <p className="mt-0.5 text-xs tabular-nums text-faint">
            {seconds}s elapsed · usually {typicalSeconds >= 60
              ? `${Math.round(typicalSeconds / 60)}–${Math.round((typicalSeconds * 2) / 60)} minutes`
              : `${typicalSeconds}–${typicalSeconds * 2} seconds`}
          </p>
        </div>
        {onStop && (
          <Button variant="ghost" size="sm" onClick={onStop}>
            Stop
          </Button>
        )}
      </div>

      <Progress value={null} label={what} className="mt-3" />

      <p aria-live="polite" className="mt-2 text-xs leading-relaxed text-muted">
        {slow
          ? 'Still going. Long documents with a lot of material take longer — nothing has gone wrong, and stopping loses nothing you typed.'
          : 'The whole document is written in one pass, so it arrives complete rather than a section at a time.'}
      </p>
    </div>
  )
}
