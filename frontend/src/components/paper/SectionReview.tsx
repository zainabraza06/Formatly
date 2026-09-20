import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { cn } from '../../lib/cn'
import { Button, Input, Spinner } from '../ui'
import { SparkIcon } from '../icons'
import type { Section } from '../../lib/paperSections'

/**
 * The finished document as a list of its sections, each with a way to have
 * that one rewritten.
 *
 * Regenerating the whole document to fix one paragraph throws away five good
 * sections to repair a sixth, which is why nobody did it. Here the rest of the
 * document is left exactly as it is.
 */
export function SectionReview({
  sections,
  busyHeading,
  disabled,
  onRegenerate,
  onJumpTo,
}: {
  sections: Section[]
  /** The heading currently being rewritten, if any. */
  busyHeading: string | null
  disabled?: boolean
  onRegenerate: (section: Section, note: string) => void
  onJumpTo?: (section: Section) => void
}) {
  const [openFor, setOpenFor] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const reduced = useReducedMotion()

  if (!sections.length) {
    return (
      <p className="text-sm text-muted">
        This document has no top-level headings, so there are no sections to rewrite
        one at a time. Regenerating rewrites the whole thing.
      </p>
    )
  }

  return (
    <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-surface">
      {sections.map((section, index) => {
        const busy = busyHeading === section.heading
        const open = openFor === section.heading

        return (
          <motion.li
            key={`${section.start}-${section.heading}`}
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.28,
              delay: Math.min(index * 0.04, 0.24),
              ease: [0.16, 1, 0.3, 1],
            }}
            className={cn('px-3 py-2.5 transition-colors', busy && 'bg-brand-soft/40')}
          >
            <div className="flex items-center gap-3">
              <div className="min-w-0 flex-1">
                {onJumpTo ? (
                  <button
                    type="button"
                    onClick={() => onJumpTo(section)}
                    className="block truncate text-left text-sm font-medium text-ink hover:text-brand-ink"
                  >
                    {section.heading}
                  </button>
                ) : (
                  <p className="truncate text-sm font-medium text-ink">{section.heading}</p>
                )}
                <p className="mt-0.5 text-2xs text-faint">
                  {busy ? 'Rewriting this section…' : `${section.words} words`}
                </p>
              </div>

              {busy ? (
                <Spinner size="sm" label={`Rewriting ${section.heading}`} />
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={disabled}
                  leadingIcon={<SparkIcon />}
                  onClick={() => {
                    setOpenFor(open ? null : section.heading)
                    setNote('')
                  }}
                  aria-expanded={open}
                >
                  Rewrite
                </Button>
              )}
            </div>

            <AnimatePresence initial={false}>
            {open && !busy && (
              <motion.div
                initial={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
                transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                className="mt-2 flex flex-col gap-2 overflow-hidden rounded-md border border-line bg-surface-2/60 p-2 sm:flex-row"
              >
                <Input
                  autoFocus
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      setOpenFor(null)
                      onRegenerate(section, note)
                    }
                    if (e.key === 'Escape') setOpenFor(null)
                  }}
                  placeholder="What should change? (optional — e.g. shorter, more detail on cost)"
                  aria-label={`What should change about ${section.heading}`}
                />
                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="md"
                    onClick={() => { setOpenFor(null); onRegenerate(section, note) }}
                  >
                    Rewrite section
                  </Button>
                  <Button variant="ghost" size="md" onClick={() => setOpenFor(null)}>
                    Cancel
                  </Button>
                </div>
              </motion.div>
            )}
            </AnimatePresence>
          </motion.li>
        )
      })}
    </ul>
  )
}
