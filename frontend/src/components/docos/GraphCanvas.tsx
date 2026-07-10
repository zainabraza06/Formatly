import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { flatten } from '../../lib/graphUtils'
import type { DocumentGraph, GraphNode } from '../../types/docos'
import { pageGeometry } from '../../types/docos'
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

function meta(n: GraphNode): Record<string, unknown> {
  return (n.metadata as Record<string, unknown> | undefined) ?? {}
}
function startsNewPage(n: GraphNode): boolean {
  return Boolean(meta(n).page_break_before)
}
function extraPages(n: GraphNode): number {
  const v = meta(n).extra_pages
  return typeof v === 'number' && v > 0 ? v : 0
}
function pageBreakCount(n: GraphNode): number {
  const v = meta(n).breaks
  return typeof v === 'number' && v > 0 ? v : 1
}

function paginate(nodes: GraphNode[]): GraphNode[][] {
  // Real page boundaries come from Word's saved layout markers; only fall back
  // to node-count chunking when the document has none.
  const hasMarkers = nodes.some(
    (n) => n.type === 'page_break' || startsNewPage(n) || extraPages(n) > 0,
  )

  const pages: GraphNode[][] = []
  let current: GraphNode[] = []
  const flush = () => {
    pages.push(current)
    current = []
  }

  for (const n of nodes) {
    if (n.type === 'page_break') {
      if (current.length) flush()
      for (let i = 0; i < pageBreakCount(n) - 1; i++) pages.push([]) // extra blank pages
      continue // the break marker itself is not rendered as content
    }
    if (startsNewPage(n) && current.length) flush()
    current.push(n)
    const spans = extraPages(n)
    if (spans > 0) {
      // node continues across additional pages (long paragraph / split table)
      flush()
      for (let i = 0; i < spans; i++) pages.push([])
    } else if (!hasMarkers && current.length >= FALLBACK_PER_PAGE) {
      flush()
    }
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
  const geo = pageGeometry(graph)
  const m = geo.margin

  return (
    <div className="flex flex-col items-center gap-4">
      {/* the "paper" — a fixed white sheet at the document's real page size */}
      <div
        className="relative overflow-hidden bg-white text-neutral-900 shadow-[0_2px_16px_rgba(0,0,0,0.22)] ring-1 ring-black/10"
        style={{
          width: `${geo.width_in}in`,
          height: `${geo.height_in}in`,
          maxWidth: '100%',
          paddingTop: `${m.top}in`,
          paddingRight: `${m.right}in`,
          paddingBottom: `${m.bottom}in`,
          paddingLeft: `${m.left}in`,
          fontFamily: 'Calibri, "Segoe UI", Cambria, Georgia, serif',
          fontSize: '11pt',
          lineHeight: 1.5,
        }}
      >
        <span className="pointer-events-none absolute right-3 top-1.5 text-[9px] font-medium uppercase tracking-wide text-neutral-300">
          Page {page + 1}
        </span>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={page}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="h-full space-y-1"
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
