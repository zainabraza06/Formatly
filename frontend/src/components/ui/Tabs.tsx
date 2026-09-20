import { useId, useRef, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../lib/cn'

export interface TabItem<T extends string> {
  id: T
  label: ReactNode
  icon?: ReactNode
  /** Announced count, e.g. the number of rows behind the tab. */
  count?: number
}

/**
 * A real tablist: arrow keys move between tabs, Home/End jump to the ends, and
 * only the selected tab is in the page's tab order. Plain buttons styled to
 * look like tabs do none of that.
 */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  size = 'md',
  label,
  className,
}: {
  items: TabItem<T>[]
  value: T
  onChange: (id: T) => void
  size?: 'sm' | 'md'
  label: string
  className?: string
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})
  // Each tablist needs its own id, or two of them on one screen would animate
  // their indicators into each other.
  const group = useId()

  const move = (dir: 1 | -1 | 'first' | 'last') => {
    const i = items.findIndex((t) => t.id === value)
    const next =
      dir === 'first' ? 0
      : dir === 'last' ? items.length - 1
      : (i + dir + items.length) % items.length
    const target = items[next]
    onChange(target.id)
    refs.current[target.id]?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn(
        'inline-flex items-center gap-0.5 rounded-md border border-line bg-surface-2 p-0.5',
        className,
      )}
      onKeyDown={(e) => {
        const map = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 } as const
        if (e.key in map) { e.preventDefault(); move(map[e.key as keyof typeof map]) }
        else if (e.key === 'Home') { e.preventDefault(); move('first') }
        else if (e.key === 'End') { e.preventDefault(); move('last') }
      }}
    >
      {items.map((tab) => {
        const selected = tab.id === value
        return (
          <button
            key={tab.id}
            ref={(el) => { refs.current[tab.id] = el }}
            role="tab"
            type="button"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative inline-flex items-center gap-1.5 rounded-sm font-medium transition-colors duration-fast ease-out',
              size === 'sm' ? 'h-7 px-2 text-xs' : 'h-8 px-3 text-sm',
              selected ? 'text-ink' : 'text-muted hover:text-ink',
            )}
          >
            {/* The white pill slides from the old tab to the new one instead of
                blinking out of one and into the other. */}
            {selected && (
              <motion.span
                layoutId={`tab-indicator-${group}`}
                className="absolute inset-0 rounded-sm bg-surface shadow-xs"
                transition={{ type: 'spring', stiffness: 520, damping: 42, mass: 0.6 }}
              />
            )}
            <span className="relative flex items-center gap-1.5">
              {tab.icon}
              {tab.label}
              {tab.count !== undefined && (
                <span className={cn('text-2xs tabular-nums', selected ? 'text-muted' : 'text-faint')}>
                  {tab.count}
                </span>
              )}
            </span>
          </button>
        )
      })}
    </div>
  )
}
