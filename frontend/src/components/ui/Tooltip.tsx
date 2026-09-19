import { useId, useState, type ReactNode } from 'react'
import { cn } from '../../lib/cn'

/**
 * A label for something that already has one in `aria-label` — the tooltip is
 * sighted-user sugar, so it is `aria-hidden` and never the only place the
 * information lives. Opens on hover and on keyboard focus, closes on Escape.
 */
export function Tooltip({
  content,
  side = 'bottom',
  children,
  className,
}: {
  content: ReactNode
  side?: 'top' | 'bottom' | 'left' | 'right'
  children: ReactNode
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const id = useId()

  const position = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-1.5',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-1.5',
    left: 'right-full top-1/2 -translate-y-1/2 mr-1.5',
    right: 'left-full top-1/2 -translate-y-1/2 ml-1.5',
  }[side]

  return (
    <span
      className={cn('relative inline-flex', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
    >
      <span aria-describedby={open ? id : undefined} className="contents">
        {children}
      </span>
      {open && (
        <span
          id={id}
          role="tooltip"
          className={cn(
            'pointer-events-none absolute z-50 w-max max-w-[15rem] animate-fade-in',
            'rounded-md bg-accent px-2 py-1 text-2xs font-medium text-accent-fg shadow-md',
            position,
          )}
        >
          {content}
        </span>
      )}
    </span>
  )
}
