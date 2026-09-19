import { Link } from 'react-router-dom'
import { cn } from '../lib/cn'

/** The wordmark. `compact` drops the name and keeps the mark, for the icon
 *  rail and for a phone header where the name would crowd out the controls. */
export function Logo({
  compact,
  to = '/app',
  className,
}: {
  compact?: boolean
  to?: string | null
  className?: string
}) {
  const content = (
    <>
      <span
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand text-sm font-bold text-brand-fg"
        aria-hidden
      >
        F
      </span>
      {!compact && <span className="text-base font-semibold tracking-tight text-ink">Formatly</span>}
    </>
  )

  const classes = cn('flex items-center gap-2 rounded-md', className)

  if (!to) {
    return (
      <span className={classes}>
        {content}
        <span className="sr-only">Formatly</span>
      </span>
    )
  }

  return (
    <Link to={to} className={classes} aria-label="Formatly — home">
      {content}
    </Link>
  )
}
