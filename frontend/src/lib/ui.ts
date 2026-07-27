// Shared class vocabulary for the editorial design system.
// Import these instead of re-typing utility strings, so every screen is consistent.
import clsx from 'clsx'

// Surfaces
export const card = 'rounded-xl border border-line bg-surface'
export const cardPad = clsx(card, 'p-5')
export const inset = 'rounded-lg border border-line bg-surface-2'

// Buttons
export const btn =
  'inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium ' +
  'transition-colors disabled:cursor-not-allowed disabled:opacity-45'
export const btnPrimary = clsx(btn, 'bg-accent text-accent-fg hover:opacity-90')
export const btnGhost = clsx(btn, 'border border-line bg-surface text-ink hover:bg-surface-2')
export const btnQuiet = clsx(btn, 'text-muted hover:bg-surface-2 hover:text-ink')

// Small pill / chip
export const chip =
  'inline-flex items-center gap-1 rounded-full border border-line bg-surface px-2.5 py-1 ' +
  'text-xs text-muted'

// Form controls
export const field =
  'w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink ' +
  'placeholder:text-faint focus:border-line-strong focus:outline-none'
export const textarea = clsx(field, 'resize-y leading-relaxed')
// Native option lists are OS-drawn and ignore translucency — keep opaque colours.
export const select =
  'w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink ' +
  'focus:border-line-strong focus:outline-none'
export const selectOption = 'bg-surface text-ink'

// Text
export const label = 'text-[11px] font-semibold uppercase tracking-wide text-muted'
export const hint = 'text-[11px] text-faint'
