import { useMemo } from 'react'
import { cn } from '../../lib/cn'
import { flatten } from '../../lib/graphUtils'
import type { DocumentGraph, GraphNode } from '../../types/docos'
import { EmptyState } from '../ui'
import { DocumentsIcon } from '../icons'

interface Entry {
  id: string
  label: string
  level: number
  type: GraphNode['type']
}

/**
 * The shape of the document: its headings, and the things between them worth
 * counting. Clicking an entry turns the canvas to it.
 *
 * It reads the same graph the assistant works on, so what is listed here is
 * what an instruction like "make all headings consistent" will act on — which
 * makes it the honest answer to "what does it think my document is".
 */
export function DocumentOutline({
  graph,
  focusId,
  onFocus,
}: {
  graph: DocumentGraph | null
  focusId?: string | null
  onFocus: (id: string) => void
}) {
  const { entries, counts } = useMemo(() => {
    const nodes = flatten(graph)
    const out: Entry[] = []
    const tally = { figures: 0, tables: 0, paragraphs: 0 }

    for (const node of nodes) {
      if (node.type === 'heading' || node.type === 'subheading') {
        out.push({
          id: node.id,
          label: node.content.trim() || 'Untitled heading',
          level: node.type === 'heading' ? 1 : 2,
          type: node.type,
        })
      } else if (node.type === 'figure' || node.type === 'image') tally.figures += 1
      else if (node.type === 'table') tally.tables += 1
      else if (node.content.trim()) tally.paragraphs += 1
    }

    return { entries: out, counts: tally }
  }, [graph])

  if (!graph) {
    return (
      <p className="text-sm text-muted">Open a document to see its structure.</p>
    )
  }

  return (
    <div className="flex h-full flex-col gap-3">
      <dl className="grid grid-cols-3 gap-2 text-center">
        <Stat label="Paragraphs" value={counts.paragraphs} />
        <Stat label="Figures" value={counts.figures} />
        <Stat label="Tables" value={counts.tables} />
      </dl>

      {entries.length === 0 ? (
        <EmptyState
          icon={<DocumentsIcon className="h-5 w-5" />}
          title="No headings"
          description="This document has no headings, so there is no outline to show. Ask the assistant to add them, or to make the ones you have consistent."
          className="py-8"
        />
      ) : (
        <nav aria-label="Document outline" className="min-h-0 flex-1 overflow-y-auto">
          <ul className="space-y-0.5">
            {entries.map((entry) => (
              <li key={entry.id}>
                <button
                  type="button"
                  onClick={() => onFocus(entry.id)}
                  aria-current={focusId === entry.id ? 'true' : undefined}
                  className={cn(
                    'block w-full truncate rounded-sm px-2 py-1.5 text-left text-sm transition-colors duration-fast',
                    entry.level === 2 && 'pl-5 text-xs',
                    focusId === entry.id
                      ? 'bg-brand-soft font-medium text-brand-ink'
                      : 'text-muted hover:bg-surface-2 hover:text-ink',
                  )}
                >
                  {entry.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-line bg-surface-2/60 px-2 py-1.5">
      <dt className="text-2xs text-faint">{label}</dt>
      <dd className="text-sm font-semibold tabular-nums text-ink">{value}</dd>
    </div>
  )
}
