import { cn } from '../../lib/cn'

/**
 * A progress bar that tells the truth: with a value it fills to it, without one
 * it sweeps, and it says which of those it is doing out loud for a screen
 * reader rather than only in pixels.
 */
export function Progress({
  value,
  label,
  className,
  tone = 'brand',
}: {
  /** 0–100. Omit for work whose length is not known yet. */
  value?: number | null
  label: string
  className?: string
  tone?: 'brand' | 'accent'
}) {
  const indeterminate = value === null || value === undefined
  const pct = indeterminate ? 0 : Math.max(0, Math.min(100, value))
  const bar = tone === 'brand' ? 'bg-brand' : 'bg-accent'

  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={indeterminate ? undefined : 0}
      aria-valuemax={indeterminate ? undefined : 100}
      aria-valuenow={indeterminate ? undefined : Math.round(pct)}
      aria-valuetext={indeterminate ? 'Working…' : `${Math.round(pct)}%`}
      className={cn('h-1.5 w-full overflow-hidden rounded-full bg-line', className)}
    >
      {indeterminate ? (
        <div className={cn('h-full w-1/3 rounded-full animate-indeterminate', bar)} />
      ) : (
        <div
          className={cn('h-full rounded-full transition-[width] duration-slow ease-out', bar)}
          style={{ width: `${pct}%` }}
        />
      )}
    </div>
  )
}
