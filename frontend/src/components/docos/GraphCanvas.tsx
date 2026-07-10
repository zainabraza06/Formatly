import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { flatten } from '../../lib/graphUtils'
import type { DocumentGraph, GraphNode } from '../../types/docos'
import { NodeView } from './NodeView'

interface Props {
  graph: DocumentGraph | null
  selectedIds: string[]
  activeId: string | null
  removingIds: string[]
}

// Fallback only: when a document carries no real page-break markers (e.g. it was
// never rendered/saved by Word), chunk by node count so we still show pages.
const FALLBACK_PER_PAGE = 40

function breaksBefore(n: GraphNode): number {
  const v = (n.metadata as Record<string, unknown> | undefined)?.page_break_before
  return typeof v === 'number' ? v : v ? 1 : 0
}

function pageBreakCount(n: GraphNode): number {
  const v = (n.metadata as Record<string, unknown> | undefined)?.breaks
  return typeof v === 'number' && v > 0 ? v : 1
}

function paginate(nodes: GraphNode[]): GraphNode[][] {
  // Real page boundaries come from Word's saved layout markers; only fall back
  // to node-count chunking when the document has none.
  const hasMarkers = nodes.some((n) => n.type === 'page_break' || breaksBefore(n) > 0)

  const pages: GraphNode[][] = []
  let current: GraphNode[] = []
  const flush = () => {
    pages.push(current)
    current = []
  }

  for (const n of nodes) {
    if (n.type === 'page_break') {
      // a blank break paragraph: end this page, plus any extra blank pages
      if (current.length) flush()
      const extra = pageBreakCount(n) - 1
      for (let i = 0; i < extra; i++) pages.push([])
      continue // the break marker itself is not rendered as content
    }
    if (breaksBefore(n) > 0 && current.length) flush()
    current.push(n)
    if (!hasMarkers && current.length >= FALLBACK_PER_PAGE) flush()
  }
  if (current.length) flush()
  return pages.length ? pages : [[]]
}

export function GraphCanvas({ graph, selectedIds, activeId, removingIds }: Props) {
  const nodes = flatten(graph)
  const pages = useMemo(() => paginate(nodes), [nodes])
  const [page, setPage] = useState(0)

  const selected = new Set(selectedIds)
  const removing = new Set(removingIds)

  // keep the page index in range as the document changes
  useEffect(() => {
    setPage((p) => Math.min(Math.max(p, 0), pages.length - 1))
  }, [pages.length])

  if (!graph) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-neutral-500">
        Import a DOCX to begin.
      </div>
    )
  }

  const total = pages.length
  const currentPage = pages[Math.min(page, total - 1)] ?? []

  return (
    <div className="flex flex-col items-center gap-4">
      {/* the "paper" — always a white Letter sheet like Word, regardless of theme */}
      <div
        className="relative space-y-1 bg-white text-neutral-900 shadow-[0_2px_12px_rgba(0,0,0,0.18)] ring-1 ring-black/10"
        style={{
          width: '8.5in',
          maxWidth: '100%',
          minHeight: '11in',
          padding: '1in',
          fontFamily: 'Calibri, "Segoe UI", Cambria, Georgia, serif',
          fontSize: '11pt',
          lineHeight: 1.5,
        }}
      >
        <span className="pointer-events-none absolute right-3 top-2 text-[10px] font-medium uppercase tracking-wide text-neutral-300">
          Page {page + 1}
        </span>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={page}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="space-y-1"
          >
            {currentPage.map((n) => (
              <NodeView
                key={n.id}
                node={n}
                selected={selected.has(n.id)}
                active={activeId === n.id}
                removing={removing.has(n.id)}
              />
            ))}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* pager controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/10 px-3 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white/5 dark:text-neutral-200"
        >
          ← Previous
        </button>
        <span className="text-xs tabular-nums text-neutral-500">
          Page {page + 1} of {total}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(total - 1, p + 1))}
          disabled={page >= total - 1}
          className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/10 px-3 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white/5 dark:text-neutral-200"
        >
          Next →
        </button>
      </div>
    </div>
  )
}
