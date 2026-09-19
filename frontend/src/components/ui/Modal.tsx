import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'
import { focusableWithin, trapTab } from '../../lib/focus'
import { Button } from './Button'

const WIDTHS = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}

/**
 * A dialog that behaves like one: focus moves into it and is trapped there,
 * Escape and the backdrop close it, the page behind it does not scroll, and
 * focus returns to whatever opened it. On a phone it arrives as a sheet from
 * the bottom, because a centred box with a keyboard open is unusable.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  /** Set for a destructive confirmation — it colours the header rule. */
  tone = 'neutral',
}: {
  open: boolean
  onClose: () => void
  title: string
  description?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  size?: keyof typeof WIDTHS
  tone?: 'neutral' | 'danger'
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  const returnTo = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return
    returnTo.current = document.activeElement as HTMLElement | null

    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'

    // Focus the first control, or the panel itself if it has none.
    const panel = panelRef.current
    const target = panel ? focusableWithin(panel)[0] ?? panel : null
    target?.focus()

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopPropagation(); onClose() }
    }
    document.addEventListener('keydown', onKey)

    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      returnTo.current?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <div
        className="absolute inset-0 animate-fade-in bg-ink/40 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        onKeyDown={(e) => panelRef.current && trapTab(panelRef.current, e)}
        className={cn(
          'relative flex max-h-[92vh] w-full flex-col overflow-hidden bg-surface shadow-xl',
          'animate-slide-up rounded-t-xl sm:animate-scale-in sm:rounded-xl',
          'border border-line',
          WIDTHS[size],
        )}
      >
        <header
          className={cn(
            'flex items-start justify-between gap-4 border-b px-5 py-4',
            tone === 'danger' ? 'border-danger/20 bg-danger-soft/40' : 'border-line',
          )}
        >
          <div className="min-w-0">
            <h2 className={cn('text-lg font-semibold', tone === 'danger' ? 'text-danger' : 'text-ink')}>
              {title}
            </h2>
            {description && <p className="mt-1 text-sm leading-relaxed text-muted">{description}</p>}
          </div>
          <Button
            variant="ghost"
            size="sm"
            iconOnly
            aria-label="Close dialog"
            onClick={onClose}
            leadingIcon={
              <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
                <path fillRule="evenodd" d="M4.28 4.28a.75.75 0 0 1 1.06 0L10 8.94l4.66-4.66a.75.75 0 1 1 1.06 1.06L11.06 10l4.66 4.66a.75.75 0 1 1-1.06 1.06L10 11.06l-4.66 4.66a.75.75 0 0 1-1.06-1.06L8.94 10 4.28 5.34a.75.75 0 0 1 0-1.06z" clipRule="evenodd" />
              </svg>
            }
          />
        </header>

        {children && <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>}

        {footer && (
          <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-line bg-surface-2/50 px-5 py-3">
            {footer}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  )
}

/** The two-button case, which is most of them. */
export function ConfirmModal({
  open, onClose, onConfirm, title, description, confirmLabel = 'Confirm',
  cancelLabel = 'Cancel', tone = 'danger', busy,
}: {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'neutral' | 'danger'
  busy?: boolean
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      size="sm"
      tone={tone}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>{cancelLabel}</Button>
          <Button
            variant={tone === 'danger' ? 'danger' : 'primary'}
            onClick={onConfirm}
            loading={busy}
          >
            {confirmLabel}
          </Button>
        </>
      }
    />
  )
}
