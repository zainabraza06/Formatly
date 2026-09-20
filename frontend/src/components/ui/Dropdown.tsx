import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'
import { Button, type ButtonSize, type ButtonVariant } from './Button'

export interface MenuItem {
  id: string
  label: string
  icon?: ReactNode
  onSelect: () => void
  /** Renders in the danger colour, below a rule separating it from the rest. */
  destructive?: boolean
  disabled?: boolean
  shortcut?: string
}

/**
 * A menu button. Up/Down walk the items, Enter picks one, Escape closes and
 * hands focus back to the trigger, and a click anywhere else dismisses it.
 *
 * The trigger is described rather than passed in, so every menu in the product
 * is the same button with the same aria wiring — and the menu owns the ref it
 * needs both to measure and to restore focus.
 *
 * The menu itself is rendered into the body rather than beside its trigger.
 * An absolutely positioned menu is clipped by any ancestor that hides its
 * overflow, and the table the library is made of is exactly that: a rounded
 * box with `overflow-hidden`, which sliced the last row's menu off ten pixels
 * short. Position it against the viewport and nothing can crop it.
 */
export function Dropdown({
  items,
  align = 'end',
  label,
  triggerLabel,
  triggerIcon,
  triggerVariant = 'secondary',
  triggerSize = 'md',
  triggerClassName,
  disabled,
}: {
  items: MenuItem[]
  align?: 'start' | 'end'
  /** Names the menu for a screen reader, and the button when it has no text. */
  label: string
  triggerLabel?: string
  triggerIcon?: ReactNode
  triggerVariant?: ButtonVariant
  triggerSize?: ButtonSize
  triggerClassName?: string
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  /** Where the menu sits, in viewport coordinates, measured as it opens. */
  const [at, setAt] = useState<{ top?: number; bottom?: number; left?: number; right?: number }>({})
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const enabled = items.filter((i) => !i.disabled)

  const close = (refocus = true) => {
    setOpen(false)
    if (refocus) triggerRef.current?.focus()
  }

  // Measured as the menu opens rather than after it has rendered: the trigger
  // is already on screen, and deciding afterwards makes the menu jump.
  const toggle = () => {
    if (open) {
      setOpen(false)
      return
    }
    const rect = triggerRef.current?.getBoundingClientRect()
    if (rect) {
      const height = Math.min(items.length * 36 + 16, 280)
      const opensUp = window.innerHeight - rect.bottom < height && rect.top > height
      setAt({
        ...(opensUp
          ? { bottom: window.innerHeight - rect.top + 4 }
          : { top: rect.bottom + 4 }),
        // Aligned to the trigger's near edge, and pinned to the viewport
        // rather than to a parent, so a menu at the right margin stays on
        // screen instead of hanging off it.
        ...(align === 'end'
          ? { right: Math.max(8, window.innerWidth - rect.right) }
          : { left: Math.max(8, rect.left) }),
      })
    }
    setActive(0)
    setOpen(true)
  }

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node
      if (!menuRef.current?.contains(t) && !triggerRef.current?.contains(t)) setOpen(false)
    }
    // A menu positioned against the viewport would drift away from its trigger
    // as the page scrolls, so it closes instead — which is what every native
    // menu does.
    const onMove = () => setOpen(false)

    document.addEventListener('mousedown', onDown)
    window.addEventListener('scroll', onMove, true)
    window.addEventListener('resize', onMove)
    return () => {
      document.removeEventListener('mousedown', onDown)
      window.removeEventListener('scroll', onMove, true)
      window.removeEventListener('resize', onMove)
    }
  }, [open])

  // The keys below are handled on the menu, so focus has to be there — a
  // callback ref does that as the element arrives, with no second render.
  const attachMenu = useCallback((el: HTMLDivElement | null) => {
    menuRef.current = el
    el?.focus()
  }, [])

  return (
    <div className="relative inline-flex">
      <Button
        ref={triggerRef}
        variant={triggerVariant}
        size={triggerSize}
        disabled={disabled}
        iconOnly={!triggerLabel}
        aria-label={triggerLabel ? undefined : label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={toggle}
        className={triggerClassName}
        leadingIcon={triggerIcon}
        trailingIcon={
          triggerLabel ? (
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 opacity-60" aria-hidden>
              <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06z" clipRule="evenodd" />
            </svg>
          ) : undefined
        }
      >
        <span className="min-w-0 flex-1 truncate text-left">{triggerLabel}</span>
      </Button>

      {open && createPortal(
        <div
          ref={attachMenu}
          style={at}
          role="menu"
          aria-label={label}
          tabIndex={-1}
          onKeyDown={(e) => {
            if (e.key === 'Escape') { e.preventDefault(); close() }
            else if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => (i + 1) % enabled.length) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => (i - 1 + enabled.length) % enabled.length) }
            else if (e.key === 'Home') { e.preventDefault(); setActive(0) }
            else if (e.key === 'End') { e.preventDefault(); setActive(enabled.length - 1) }
            else if (e.key === 'Tab') { e.preventDefault(); close() }
            else if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              const item = enabled[active]
              if (item) { close(); item.onSelect() }
            }
          }}
          className="fixed z-50 min-w-[11rem] max-w-[calc(100vw-1rem)] animate-scale-in rounded-lg border border-line bg-surface p-1 shadow-lg outline-none"
        >
          {items.map((item, i) => {
            const idx = enabled.indexOf(item)
            const isActive = idx === active
            return (
              <button
                key={item.id}
                role="menuitem"
                type="button"
                disabled={item.disabled}
                tabIndex={-1}
                onMouseEnter={() => idx >= 0 && setActive(idx)}
                onClick={() => { close(false); item.onSelect() }}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-sm px-2 py-1.5 text-left text-sm transition-colors duration-fast',
                  item.destructive ? 'text-danger' : 'text-ink',
                  isActive && !item.disabled && (item.destructive ? 'bg-danger-soft' : 'bg-surface-2'),
                  item.disabled && 'cursor-not-allowed opacity-50',
                  item.destructive && i > 0 && 'mt-1 border-t border-line pt-2',
                )}
              >
                {item.icon && (
                  <span className={cn('shrink-0', item.destructive ? 'text-danger' : 'text-faint')}>
                    {item.icon}
                  </span>
                )}
                <span className="flex-1 truncate">{item.label}</span>
                {item.shortcut && <kbd className="text-2xs text-faint">{item.shortcut}</kbd>}
              </button>
            )
          })}
        </div>,
        document.body,
      )}
    </div>
  )
}
