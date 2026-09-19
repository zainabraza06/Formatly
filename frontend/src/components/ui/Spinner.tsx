import { cn } from '../../lib/cn'

const SIZES = { sm: 'h-3.5 w-3.5', md: 'h-4 w-4', lg: 'h-6 w-6' }

/** A determinate-looking ring for work with no measurable progress. */
export function Spinner({
  size = 'md',
  className,
  label,
}: {
  size?: keyof typeof SIZES
  className?: string
  label?: string
}) {
  return (
    <span
      role={label ? 'status' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={cn('inline-block shrink-0', SIZES[size], className)}
    >
      <svg viewBox="0 0 24 24" fill="none" className="h-full w-full animate-spin">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
        <path
          d="M21 12a9 9 0 0 0-9-9"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
    </span>
  )
}
