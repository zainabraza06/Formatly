import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'
import { ToastContext, type Toast, type ToastApi, type ToastTone } from './toast-context'

const DEFAULT_DURATION: Record<ToastTone, number | null> = {
  success: 4000,
  info: 5000,
  error: 8000,   // an error usually asks the reader to do something: give them time
  loading: null, // until it is replaced
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const timers = useRef<Record<string, number>>({})

  const dismiss = useCallback((id: string) => {
    window.clearTimeout(timers.current[id])
    delete timers.current[id]
    setToasts((all) => all.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback<ToastApi['toast']>((input) => {
    const id = input.id ?? `t${Date.now()}${Math.random().toString(16).slice(2, 6)}`
    const next: Toast = {
      duration: input.duration === undefined ? DEFAULT_DURATION[input.tone] : input.duration,
      ...input,
      id,
    }
    setToasts((all) => {
      const at = all.findIndex((t) => t.id === id)
      if (at >= 0) {
        const copy = [...all]
        copy[at] = next
        return copy
      }
      // Four is as many as anyone reads; the oldest goes.
      return [...all, next].slice(-4)
    })

    window.clearTimeout(timers.current[id])
    if (next.duration) {
      timers.current[id] = window.setTimeout(() => dismiss(id), next.duration)
    }
    return id
  }, [dismiss])

  const api = useMemo<ToastApi>(() => ({
    toast,
    dismiss,
    success: (title, description) => toast({ tone: 'success', title, description }),
    error: (title, description) => toast({ tone: 'error', title, description }),
    info: (title, description) => toast({ tone: 'info', title, description }),
    loading: (title, description) => toast({ tone: 'loading', title, description }),
  }), [toast, dismiss])

  useEffect(() => () => {
    Object.values(timers.current).forEach(window.clearTimeout)
  }, [])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

function ToastViewport({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  if (typeof document === 'undefined') return null

  return createPortal(
    // Bottom-right on a desktop; across the bottom on a phone, where the top of
    // the screen is the furthest point from the reader's thumb.
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 p-4 sm:inset-x-auto sm:right-0 sm:items-end">
      {/* Polite for ordinary news, assertive for errors: a failure is worth
          interrupting for, a saved file is not. */}
      <div aria-live="polite" aria-atomic="false" className="contents">
        {toasts.filter((t) => t.tone !== 'error').map((t) => (
          <ToastCard key={t.id} toast={t} onDismiss={onDismiss} />
        ))}
      </div>
      <div aria-live="assertive" aria-atomic="false" className="contents">
        {toasts.filter((t) => t.tone === 'error').map((t) => (
          <ToastCard key={t.id} toast={t} onDismiss={onDismiss} />
        ))}
      </div>
    </div>,
    document.body,
  )
}

const TONE_STYLES: Record<ToastTone, { ring: string; icon: ReactNode }> = {
  success: {
    ring: 'text-success',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
        <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5z" clipRule="evenodd" />
      </svg>
    ),
  },
  error: {
    ring: 'text-danger',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
        <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0zm-8-5a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0v-4.5A.75.75 0 0 1 10 5zm0 9.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2z" clipRule="evenodd" />
      </svg>
    ),
  },
  info: {
    ring: 'text-info',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden>
        <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0zm-9-3.5a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM10 9a.75.75 0 0 1 .75.75v4a.75.75 0 0 1-1.5 0v-4A.75.75 0 0 1 10 9z" clipRule="evenodd" />
      </svg>
    ),
  },
  loading: {
    ring: 'text-brand-ink',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 animate-spin" aria-hidden>
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
        <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    ),
  },
}

function ToastCard({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const tone = TONE_STYLES[toast.tone]
  return (
    <div className="pointer-events-auto flex w-full max-w-sm animate-fade-up items-start gap-3 rounded-lg border border-line bg-surface p-3 shadow-lg">
      <span className={cn('mt-0.5 shrink-0', tone.ring)}>{tone.icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">{toast.title}</p>
        {toast.description && (
          <p className="mt-0.5 text-xs leading-relaxed text-muted">{toast.description}</p>
        )}
        {toast.action && (
          <button
            type="button"
            onClick={() => { toast.action?.onClick(); onDismiss(toast.id) }}
            className="mt-2 rounded-sm text-xs font-semibold text-brand-ink hover:underline"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        className="-m-1 shrink-0 rounded-sm p-1 text-faint transition-colors hover:text-ink"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5" aria-hidden>
          <path fillRule="evenodd" d="M4.28 4.28a.75.75 0 0 1 1.06 0L10 8.94l4.66-4.66a.75.75 0 1 1 1.06 1.06L11.06 10l4.66 4.66a.75.75 0 1 1-1.06 1.06L10 11.06l-4.66 4.66a.75.75 0 0 1-1.06-1.06L8.94 10 4.28 5.34a.75.75 0 0 1 0-1.06z" clipRule="evenodd" />
        </svg>
      </button>
    </div>
  )
}
