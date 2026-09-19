import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

/**
 * A surface with a hairline. No resting shadow: elevation is for things that
 * float, and a border plus a shadow on every panel is what makes an interface
 * look like a pile of boxes. `interactive` adds the hover affordance, and is
 * only for a card that is entirely clickable.
 */
export function Card({
  className,
  interactive,
  padded = true,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { interactive?: boolean; padded?: boolean }) {
  return (
    <div
      className={cn(
        'rounded-lg border border-line bg-surface',
        padded && 'p-4 sm:p-5',
        interactive &&
          'transition-colors duration-fast ease-out hover:border-line-strong hover:bg-surface-2/40',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  title,
  description,
  action,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex items-start justify-between gap-3', className)}>
      <div className="min-w-0">
        <h2 className="text-base font-medium text-ink">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
