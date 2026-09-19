import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

/** A surface with a border. `interactive` adds the hover affordance — use it
 *  only when the whole card is clickable. */
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
        'rounded-lg border border-line bg-surface shadow-xs',
        padded && 'p-5',
        interactive &&
          'transition-[border-color,box-shadow] duration-fast ease-out hover:border-line-strong hover:shadow-sm',
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
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
