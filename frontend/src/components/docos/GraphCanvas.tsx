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

// Max content nodes per page before we start a new one (explicit page breaks
// always start a new page regardless of this cap).
const MAX_PER_PAGE = 12

function paginate(nodes: GraphNode[]): GraphNode[][] {
  const pages: GraphNode[][] = []
  let current: GraphNode[] = []
  for (const n of nodes) {
    if (n.type === 'page_break') {
      current.push(n)
      pages.push(current)
      current = []
      continue
    }
    current.push(n)
    if (current.length >= MAX_PER_PAGE) {
      pages.push(current)
      current = []
    }
  }
  if (current.length) pages.push(current)
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
    <div className="mx-auto flex max-w-3xl flex-col items-center gap-3">
      {/* the "paper" */}
      <div className="relative min-h-[70vh] w-full space-y-1 rounded-2xl bg-white px-8 py-10 shadow-sm dark:bg-neutral-950/60">
        <span className="pointer-events-none absolute right-4 top-3 text-[10px] font-medium uppercase tracking-wide text-neutral-300 dark:text-neutral-600">
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
