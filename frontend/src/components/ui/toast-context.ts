import { createContext, useContext } from 'react'

export type ToastTone = 'success' | 'error' | 'info' | 'loading'

export interface Toast {
  id: string
  tone: ToastTone
  title: string
  description?: string
  /** One button, for the thing the toast is about: "Undo", "Open", "Retry". */
  action?: { label: string; onClick: () => void }
  /** ms; null keeps it until it is dismissed or replaced. */
  duration?: number | null
}

export interface ToastApi {
  toast: (t: Omit<Toast, 'id'> & { id?: string }) => string
  success: (title: string, description?: string) => string
  error: (title: string, description?: string) => string
  info: (title: string, description?: string) => string
  /** A toast that stays until the work it names finishes. Returns its id, so
   *  the caller can replace it with the outcome rather than stacking a second. */
  loading: (title: string, description?: string) => string
  dismiss: (id: string) => void
}

export const ToastContext = createContext<ToastApi | null>(null)

/** Feedback for something that happened, in place of an unstyleable alert(). */
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
