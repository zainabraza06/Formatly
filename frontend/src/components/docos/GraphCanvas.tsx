import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { flatten } from '../../lib/graphUtils'
import type { DocumentGraph, GraphNode } from '../../types/docos'
import type { DiffMark } from '../../lib/diffMarks'
import { pageGeometry } from '../../types/docos'
import { measurePages, type Measured } from './measurePages'
import { NodeView } from './NodeView'

interface Props {
  graph: DocumentGraph | null
  selectedIds: string[]
  activeId: string | null
  removingIds: string[]
  /** Nodes a compare result names, keyed by id. Empty when no diff is open. */
  marks?: Map<string, DiffMark>
  /** Turn to the page holding this node — the assistant is working there. */
  focusId?: string | null
  /** Draw LaTeX typed into the text as mathematics, because the reader asked. */
  renderMaths?: boolean
}

// Fallback only: when a document carries no real page-break markers (e.g. it was
// never rendered/saved by Word), chunk by node count so we still show pages.
const FALLBACK_PER_PAGE = 40

// CSS defines an inch as exactly 96px, so the page's real text box is known from
// the geometry alone. Reading it off the rendered sheet instead was wrong twice
// over: before the first measurement the sheet is only min-height, so it is as
// tall as whatever content it happens to hold, and once it is scaled to fit its
// column every measurement off it comes back scaled too.
const PX_PER_INCH = 96

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

function pageIndex(n: GraphNode): number | null {
  const v = meta(n).page_index
  return typeof v === 'number' ? v : null
}

function paginate(nodes: GraphNode[], exactCount?: number): GraphNode[][] {
  // Best case: LibreOffice gave every node an exact page_index — group by it.
  if (nodes.some((n) => pageIndex(n) !== null)) {
    const maxIdx = nodes.reduce((m, n) => Math.max(m, pageIndex(n) ?? 0), 0)
    const count = Math.max(maxIdx + 1, exactCount ?? 0)
    const pages: GraphNode[][] = Array.from({ length: count }, () => [])
    for (const n of nodes) pages[Math.min(pageIndex(n) ?? 0, count - 1)].push(n)
    return pages
  }

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

export function GraphCanvas({
  graph, selectedIds, activeId, removingIds, marks, focusId, renderMaths,
}: Props) {
  const nodes = flatten(graph)
  const geo = pageGeometry(graph)

  // Word's markers describe a layout that is not the one on screen, so they are
  // only the starting point: the content is laid out once off screen at the real
  // text width and the measured heights decide where the pages actually break.
  const markerPages = useMemo(() => paginate(nodes, geo.count), [nodes, geo.count])

  // A numbered item's number is its place in its own run of items, counted in
  // document order. It has to be worked out here, over the whole document, and
  // not inside the page: a list that crosses a page boundary would otherwise
  // start again at 1 on the next sheet.
  const listOrdinals = useMemo(() => {
    const out = new Map<string, number>()
    let run = 0
    let kind = ''
    for (const n of nodes) {
      const listing = (n.metadata ?? {})['list'] as { kind?: string } | undefined
      const k = listing ? String(listing.kind ?? 'bullet') : ''
      run = k && k === kind ? run + 1 : k ? 1 : 0
      kind = k
      if (k === 'number') out.set(n.id, run)
    }
    return out
  }, [nodes])
  const [measuredPages, setMeasuredPages] = useState<GraphNode[][] | null>(null)
  const sheetRef = useRef<HTMLDivElement>(null)
  const proofRef = useRef<HTMLDivElement>(null)
  const frameRef = useRef<HTMLDivElement>(null)
  // A page too wide for its column is shown smaller, never squeezed: shrinking
  // the sheet's width would re-wrap every line and stop it being a page of this
  // document at all. 1 until measured, so a page that fits is untouched.
  const [scale, setScale] = useState(1)
  // Measured, not assumed: every face has its own natural line height, and it
  // is what Word's "1.15 line spacing" is a multiple of.
  const [naturalLineHeight, setNaturalLineHeight] = useState(1.15)

  useLayoutEffect(() => {
    const measure = () => {
      const probe = document.createElement('div')
      probe.textContent = 'Hxg'
      probe.setAttribute('aria-hidden', 'true')
      Object.assign(probe.style, {
        position: 'absolute', left: '-9999px', top: '0', lineHeight: 'normal',
        fontFamily: geo.default_font
          ? `"${geo.default_font}", Cambria, Georgia, serif`
          : 'Calibri, "Segoe UI", Cambria, Georgia, serif',
        fontSize: `${geo.default_size_pt || 11}pt`,
      })
      document.body.appendChild(probe)
      const size = parseFloat(getComputedStyle(probe).fontSize)
      const height = probe.getBoundingClientRect().height
      document.body.removeChild(probe)
      if (size > 0 && height > 0) setNaturalLineHeight(height / size)
    }

    measure()
    // A face that arrives late has different metrics from the fallback that
    // stood in for it, and every page break depends on them.
    let cancelled = false
    document.fonts?.ready.then(() => { if (!cancelled) measure() }).catch(() => {})
    return () => { cancelled = true }
  }, [geo.default_font, geo.default_size_pt])

  useLayoutEffect(() => {
    const frame = frameRef.current
    if (!frame) return
    const fit = () => {
      const available = frame.clientWidth
      if (available > 0) setScale(Math.min(1, available / (geo.width_in * PX_PER_INCH)))
    }
    fit()
    const observer = new ResizeObserver(fit)
    observer.observe(frame)
    return () => observer.disconnect()
  }, [geo.width_in])

  useLayoutEffect(() => {
    const proof = proofRef.current
    if (!proof || !nodes.length) return

    const textHeight = (geo.height_in - geo.margin.top - geo.margin.bottom) * PX_PER_INCH
    if (!(textHeight > 0)) return

    const children = Array.from(proof.children) as HTMLElement[]
    const proofBottom = proof.getBoundingClientRect().height
    const measured: Measured[] = []
    nodes.forEach((node, i) => {
      const element = children[i]
      if (!element) return
      // Distance to the next sibling, so the gap between nodes is counted.
      const next = children[i + 1]
      const height = next
        ? next.offsetTop - element.offsetTop
        : proofBottom - element.offsetTop
      measured.push({
        node, element,
        height: Math.max(0, height),
        own: element.getBoundingClientRect().height,
      })
    })
    setMeasuredPages(measurePages(measured, textHeight))
    // `marks` changes the text on the page (struck-out words are still words),
    // so a diff opening or closing has to be measured again. The display scale
    // is deliberately absent: it changes how big the page looks, never how the
    // text wraps inside it.
  }, [nodes, marks, renderMaths, naturalLineHeight, geo.width_in, geo.height_in,
      geo.margin.top, geo.margin.bottom, geo.default_font, geo.default_size_pt])

  const pages = measuredPages ?? markerPages
  const [page, setPage] = useState(0)

  const selected = new Set(selectedIds)
  const removing = new Set(removingIds)

  // Keep the page index in range as the document changes, and follow the
  // assistant to the page it is working on. A node split across a page boundary
  // carries a suffixed id, so the base id is what is matched.
  useEffect(() => {
    setPage((current) => {
      const clamped = Math.min(Math.max(current, 0), pages.length - 1)
      if (!focusId) return clamped
      const base = (id: string) => id.split('~')[0]
      const found = pages.findIndex((nodes) => nodes.some((n) => base(n.id) === base(focusId)))
      return found >= 0 ? found : clamped
    })
  }, [pages, focusId])

  if (!graph) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Import a DOCX to begin.
      </div>
    )
  }

  const total = pages.length
  const currentPage = pages[Math.min(page, total - 1)] ?? []
  const m = geo.margin

  // Typography shared by the sheet and the measuring pass. They must be
  // identical: a measurement taken at a different size or face describes a
  // layout nobody will see.
  const typography = {
    fontFamily: geo.default_font
      ? `"${geo.default_font}", Cambria, Georgia, serif`
      : 'Calibri, "Segoe UI", Cambria, Georgia, serif',
    fontSize: `${geo.default_size_pt || 11}pt`,
    lineHeight: 1.15,
  } as const

  return (
    <div className="flex flex-col items-center gap-4">
      {/* The measuring pass: every node laid out once at the page's real text
          width, off screen. aria-hidden because it is a ruler, not content. */}
      <div
        ref={proofRef}
        aria-hidden
        className="pointer-events-none absolute -left-[9999px] top-0"
        style={{
          width: `calc(${geo.width_in}in - ${m.left}in - ${m.right}in)`,
          ...typography,
        }}
      >
        {nodes.map((n) => (
          <NodeView
            key={n.id}
            node={n}
            selected={false}
            active={false}
            removing={false}
            mark={marks?.get(n.id)}
            naturalLineHeight={naturalLineHeight}
            renderMaths={renderMaths}
            listIndex={listOrdinals.get(n.id)}
          />
        ))}
      </div>

      {/* The frame owns the space the scaled page takes up; the sheet inside it
          keeps the document's true dimensions. */}
      <div
        ref={frameRef}
        className="flex w-full justify-center overflow-hidden"
        style={{ height: `${geo.height_in * PX_PER_INCH * scale}px` }}
      >
      {/* the "paper" — a fixed white sheet at the document's real page size */}
      <div
        ref={sheetRef}
        className="relative bg-white text-neutral-900 shadow-[0_2px_16px_rgba(0,0,0,0.22)] ring-1 ring-black/10"
        style={{
          width: `${geo.width_in}in`,
          // A real page height again: the pages are now filled from measured
          // heights, so what is on a page is what fits on it. minHeight stays
          // as the floor so a short last page is still a full sheet.
          height: measuredPages ? `${geo.height_in}in` : undefined,
          minHeight: `${geo.height_in}in`,
          transform: `scale(${scale})`,
          transformOrigin: 'top center',
          flex: '0 0 auto',
          paddingTop: `${m.top}in`,
          paddingRight: `${m.right}in`,
          paddingBottom: `${m.bottom}in`,
          paddingLeft: `${m.left}in`,
          // The document's own typeface and size, falling back only when the
          // file names neither.
          ...typography,
        }}
      >
        <span className="pointer-events-none absolute right-3 top-1.5 text-[9px] font-medium uppercase tracking-wide text-neutral-300">
          Page {page + 1}
        </span>
        {/* `mode="wait"` empties the sheet between pages: the outgoing page has
            to finish leaving before the incoming one is mounted, so every turn
            shows blank paper for the length of the animation. On a forty-page
            document that is most of what paging through it looks like. The
            pages cross-fade in place instead, and briskly. */}
        <AnimatePresence initial={false}>
          <motion.div
            key={page}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="absolute inset-0 h-full"
            style={{ padding: `${m.top}in ${m.right}in ${m.bottom}in ${m.left}in` }}
          >
            {currentPage.map((n) => (
              <NodeView
                key={n.id}
                node={n}
                selected={selected.has(n.id)}
                active={activeId === n.id}
                removing={removing.has(n.id)}
                mark={marks?.get(n.id)}
                naturalLineHeight={naturalLineHeight}
                renderMaths={renderMaths}
                listIndex={listOrdinals.get(n.id)}
              />
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
      </div>

      {/* pager controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
          className="flex items-center gap-1 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
        >
          ← Previous
        </button>
        <span className="text-xs tabular-nums text-muted">
          Page {page + 1} of {total}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(total - 1, p + 1))}
          disabled={page >= total - 1}
          className="flex items-center gap-1 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </div>
  )
}
