import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../../lib/cn'

export interface Command {
  id: string
  label: string
  /** Groups the list: "Go to", "Document", "Create"… */
  group: string
  icon?: ReactNode
  /** Extra words to match on that are not in the label. */
  keywords?: string
  shortcut?: string[]
  run: () => void
  disabled?: boolean
}

/**
 * Cmd/Ctrl+K. Every command in the product is reachable from here by typing
 * part of its name, which is also the answer to "where is that button" for
 * anyone who cannot find it.
 *
 * Matching is subsequence-based, the way editors do it: "nd" finds
 * "New document".
 */
export function CommandPalette({ open, onClose, commands }: {
  open: boolean
  onClose: () => void
  commands: Command[]
}) {
  if (!open) return null
  return <Palette onClose={onClose} commands={commands} />
}

function Palette({ onClose, commands }: { onClose: () => void; commands: Command[] }) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const returnTo = useRef<HTMLElement | null>(null)

  const matches = useMemo(() => {
    const usable = commands.filter((c) => !c.disabled)
    if (!query.trim()) return usable
    return usable
      .map((c) => ({ c, score: score(`${c.label} ${c.group} ${c.keywords ?? ''}`, query) }))
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((r) => r.c)
  }, [commands, query])

  const groups = useMemo(() => {
    const out = new Map<string, Command[]>()
    for (const c of matches) out.set(c.group, [...(out.get(c.group) ?? []), c])
    return [...out.entries()]
  }, [matches])

  // The palette is mounted only while it is open (and remounted each time),
  // so the query and the highlight start fresh without being reset here.
  useEffect(() => {
    returnTo.current = document.activeElement as HTMLElement | null
    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'
    // The input is focused by autoFocus; this hands focus back on the way out.
    return () => {
      document.body.style.overflow = overflow
      returnTo.current?.focus?.()
    }
  }, [])

  // Keep the highlighted row in view when arrowing past the fold.
  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>('[data-active="true"]')
      ?.scrollIntoView({ block: 'nearest' })
  }, [active])

  const pick = (cmd: Command | undefined) => {
    if (!cmd) return
    onClose()
    // After the palette has closed, so a command that focuses something wins.
    window.setTimeout(() => cmd.run(), 0)
  }

  return createPortal(
    <div className="fixed inset-0 z-[70] flex items-start justify-center p-4 pt-[10vh]">
      <div className="absolute inset-0 animate-fade-in bg-ink/40 backdrop-blur-[2px]" onClick={onClose} aria-hidden />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="relative flex max-h-[70vh] w-full max-w-xl animate-scale-in flex-col overflow-hidden rounded-xl border border-line bg-surface shadow-xl"
        onKeyDown={(e) => {
          if (e.key === 'Escape') { e.preventDefault(); onClose() }
          else if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => Math.min(i + 1, matches.length - 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)) }
          else if (e.key === 'Home') { e.preventDefault(); setActive(0) }
          else if (e.key === 'End') { e.preventDefault(); setActive(matches.length - 1) }
          else if (e.key === 'Enter') { e.preventDefault(); pick(matches[active]) }
          else if (e.key === 'Tab') { e.preventDefault() } // nothing to tab to; the list is the UI
        }}
      >
        <div className="flex items-center gap-2.5 border-b border-line px-4">
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 shrink-0 text-faint" aria-hidden>
            <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 1 0 3.383 9.836l3.14 3.141a.75.75 0 1 0 1.061-1.06l-3.14-3.141A5.5 5.5 0 0 0 9 3.5zM5 9a4 4 0 1 1 8 0 4 4 0 0 1-8 0z" clipRule="evenodd" />
          </svg>
          <input
            ref={inputRef}
            autoFocus
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActive(0) }}
            placeholder="Search commands…"
            aria-label="Search commands"
            aria-controls="command-results"
            aria-activedescendant={matches[active] ? `cmd-${matches[active].id}` : undefined}
            className="h-12 flex-1 bg-transparent text-md text-ink outline-none placeholder:text-faint"
          />
          <kbd className="hidden shrink-0 rounded-sm border border-line px-1.5 py-0.5 text-2xs text-faint sm:block">
            Esc
          </kbd>
        </div>

        <div id="command-results" ref={listRef} role="listbox" aria-label="Commands" className="min-h-0 flex-1 overflow-y-auto p-1.5">
          {matches.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted">
              Nothing matches “{query}”.
            </p>
          ) : (
            groups.map(([group, items]) => (
              <div key={group} className="mb-1 last:mb-0">
                <p className="px-2.5 py-1.5 text-2xs font-semibold uppercase tracking-wide text-faint">
                  {group}
                </p>
                {items.map((cmd) => {
                  const index = matches.indexOf(cmd)
                  const isActive = index === active
                  return (
                    <div
                      key={cmd.id}
                      id={`cmd-${cmd.id}`}
                      role="option"
                      aria-selected={isActive}
                      data-active={isActive}
                      onMouseEnter={() => setActive(index)}
                      onClick={() => pick(cmd)}
                      className={cn(
                        'flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm',
                        isActive ? 'bg-brand-soft text-brand-ink' : 'text-ink',
                      )}
                    >
                      {cmd.icon && <span className={cn('shrink-0', isActive ? 'text-brand-ink' : 'text-faint')}>{cmd.icon}</span>}
                      <span className="flex-1 truncate">{cmd.label}</span>
                      {cmd.shortcut && (
                        <span className="flex shrink-0 gap-1">
                          {cmd.shortcut.map((k) => (
                            <kbd key={k} className="rounded-sm border border-line bg-surface px-1.5 py-0.5 text-2xs text-faint">
                              {k}
                            </kbd>
                          ))}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            ))
          )}
        </div>

        <footer className="flex items-center gap-4 border-t border-line bg-surface-2/60 px-4 py-2 text-2xs text-faint">
          <span><kbd className="font-sans">↑↓</kbd> navigate</span>
          <span><kbd className="font-sans">↵</kbd> run</span>
          <span><kbd className="font-sans">esc</kbd> close</span>
        </footer>
      </div>
    </div>,
    document.body,
  )
}

/**
 * Subsequence match, weighted so that a hit at a word boundary counts for more
 * than one in the middle of a word — "nd" should find "New document" before
 * "Kind of thing".
 */
function score(haystack: string, needle: string): number {
  const h = haystack.toLowerCase()
  const n = needle.toLowerCase().replace(/\s+/g, '')
  if (!n) return 1
  let i = 0
  let points = 0
  for (const ch of n) {
    const at = h.indexOf(ch, i)
    if (at === -1) return 0
    points += at === 0 || h[at - 1] === ' ' ? 3 : 1
    i = at + 1
  }
  // A shorter haystack matching the same letters is the better match.
  return points + Math.max(0, 20 - h.length / 4)
}
