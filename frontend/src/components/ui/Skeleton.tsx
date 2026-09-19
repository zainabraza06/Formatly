import { cn } from '../../lib/cn'

/**
 * A placeholder shaped like the thing that is coming. It is aria-hidden: the
 * region it sits in carries the `aria-busy`, so a screen reader hears "loading"
 * once rather than a bar per grey rectangle.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn(
        'relative overflow-hidden rounded-sm bg-surface-2',
        'after:absolute after:inset-0 after:-translate-x-full after:animate-shimmer',
        'after:bg-gradient-to-r after:from-transparent after:via-line/70 after:to-transparent',
        className,
      )}
    />
  )
}

/** Several lines of text, the last one short, the way real text ends. */
export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={cn('h-3', i === lines - 1 ? 'w-2/5' : 'w-full')} />
      ))}
    </div>
  )
}
