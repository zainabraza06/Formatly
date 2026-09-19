import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

/**
 * What a screen says when it has nothing to show. It always names the one
 * thing to do next — an empty screen with no way forward is a dead end.
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  tone = 'empty',
  className,
}: {
  icon?: ReactNode
  title: string
  description?: ReactNode
  action?: ReactNode
  secondaryAction?: ReactNode
  /** `error` is the same shape, in the colour of something having gone wrong. */
  tone?: 'empty' | 'error'
  className?: string
}) {
  const isError = tone === 'error'
  return (
    <div
      role={isError ? 'alert' : undefined}
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center',
        isError ? 'border-danger/30 bg-danger-soft/50' : 'border-line bg-surface-2/40',
        className,
      )}
    >
      {icon && (
        <div
          className={cn(
            'mb-3 flex h-11 w-11 items-center justify-center rounded-lg border',
            isError ? 'border-danger/20 bg-surface text-danger' : 'border-line bg-surface text-faint',
          )}
          aria-hidden
        >
          {icon}
        </div>
      )}
      <p className={cn('text-base font-semibold', isError ? 'text-danger' : 'text-ink')}>{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-sm leading-relaxed text-muted">{description}</p>
      )}
      {(action || secondaryAction) && (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          {action}
          {secondaryAction}
        </div>
      )}
    </div>
  )
}
