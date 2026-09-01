// Shared class vocabulary for the editorial design system.
import clsx from 'clsx'

// Surfaces
export const card = 'rounded-2xl border border-line bg-surface shadow-sm'
export const cardPad = clsx(card, 'p-6')
export const inset = 'rounded-xl border border-line bg-surface-2 p-4'

// Buttons
export const btn =
  'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold ' +
  'transition-all duration-200 ease-out disabled:cursor-not-allowed disabled:opacity-50'
export const btnPrimary = clsx(btn, 'bg-focus text-white shadow-md shadow-focus/20 hover:shadow-lg hover:shadow-focus/30 hover:-translate-y-0.5 active:translate-y-0')
export const btnGhost = clsx(btn, 'border border-line bg-surface text-ink hover:bg-surface-2 hover:border-line-strong shadow-sm hover:shadow')
export const btnQuiet = clsx(btn, 'text-muted hover:bg-surface-2 hover:text-ink active:scale-95')

// Small pill / chip
export const chip =
  'inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 ' +
  'text-xs font-medium text-muted transition-colors hover:text-ink hover:bg-surface-2'

// Form controls
export const field =
  'w-full rounded-xl border border-line bg-surface px-4 py-2.5 text-sm text-ink ' +
  'placeholder:text-faint focus:border-focus focus:ring-2 focus:ring-focus/20 focus:outline-none transition-shadow'
export const textarea = clsx(field, 'resize-y leading-relaxed')

export const select =
  'w-full rounded-xl border border-line bg-surface px-4 py-2.5 text-sm text-ink ' +
  'focus:border-focus focus:ring-2 focus:ring-focus/20 focus:outline-none transition-shadow'
export const selectOption = 'bg-surface text-ink'

// Text
export const label = 'text-xs font-semibold uppercase tracking-wider text-muted'
export const hint = 'text-xs text-faint'

