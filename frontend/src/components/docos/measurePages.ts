import type { GraphNode } from '../../types/docos'

/** Pagination by measurement.
 *
 *  Assigning nodes to pages from Word's saved markers and then rendering them
 *  at different metrics does not work: the browser needs more or less room than
 *  Word did, so a page either overflows or ends short. The markers describe a
 *  layout that is not the one on screen.
 *
 *  So the content is laid out once, off screen, at the exact width of the page's
 *  text area, and the real heights decide the breaks. The browser keeps doing
 *  the line breaking — which it is good at — and only the page filling is ours.
 */

/** A paragraph must not leave fewer than this many lines behind, or carry fewer
 *  than this many over. One line stranded on its own reads as a mistake. */
const MIN_LINES = 2

/** Node types whose text can be broken across a page boundary. A table or a
 *  picture moves whole; splitting one would mean rebuilding it. */
const SPLITTABLE = new Set(['body', 'paragraph', 'reference', 'footnote', 'caption'])

function meta(node: GraphNode): Record<string, unknown> {
  return (node.metadata as Record<string, unknown> | undefined) ?? {}
}

function startsNewPage(node: GraphNode): boolean {
  return Boolean(meta(node).page_break_before)
}

function pageBreakCount(node: GraphNode): number {
  const v = meta(node).breaks
  return typeof v === 'number' && v > 0 ? v : 1
}

/** The largest character offset whose text still fits in `maxHeight`. */
function offsetThatFits(element: HTMLElement, maxHeight: number): number | null {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT)
  const text = walker.nextNode() as Text | null
  if (!text || !text.data.trim()) return null

  const range = document.createRange()
  const height = (end: number): number => {
    range.setStart(text, 0)
    range.setEnd(text, end)
    return range.getBoundingClientRect().height
  }

  let lo = 0
  let hi = text.data.length
  let best = 0
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (height(mid) <= maxHeight) {
      best = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  if (best <= 0 || best >= text.data.length) return null

  // Break on a word, not mid-word.
  const space = text.data.lastIndexOf(' ', best)
  return space > 0 ? space : null
}

/** One line's height, used to keep a stray line off a page on its own. */
function lineHeight(element: HTMLElement): number {
  const parsed = parseFloat(getComputedStyle(element).lineHeight)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 16
}

function sliced(node: GraphNode, content: string, suffix: string): GraphNode {
  return { ...node, id: `${node.id}${suffix}`, content }
}

export interface Measured {
  node: GraphNode
  element: HTMLElement
  /** Height including the gap that follows it. Taken from the distance to the
   *  next sibling rather than the element's own box, so the spacing between
   *  nodes is counted — leaving it out overflows every page by the gaps. */
  height: number
}

/**
 * Fill pages from measured heights.
 *
 * `pageHeight` is the height of the page's text area in the same pixels the
 * elements were measured in.
 */
export function measurePages(measured: Measured[], pageHeight: number): GraphNode[][] {
  if (!measured.length || pageHeight <= 0) return [[]]

  const pages: GraphNode[][] = []
  let current: GraphNode[] = []
  let used = 0

  const flush = (): void => {
    pages.push(current)
    current = []
    used = 0
  }

  for (const { node, element, height } of measured) {
    if (node.type === 'page_break') {
      flush()
      for (let i = 1; i < pageBreakCount(node); i++) pages.push([])
      continue
    }
    if (startsNewPage(node) && current.length) flush()

    const remaining = pageHeight - used

    if (height <= remaining) {
      current.push(node)
      used += height
      continue
    }

    // Too tall for what is left. Try to break the text across the boundary,
    // but only when both halves keep enough lines to look deliberate.
    const line = lineHeight(element)
    const canSplit = SPLITTABLE.has(node.type) && typeof node.content === 'string'
    if (canSplit && remaining >= line * MIN_LINES && height - remaining >= line * MIN_LINES) {
      const offset = offsetThatFits(element, remaining)
      if (offset) {
        const head = node.content.slice(0, offset).trimEnd()
        const tail = node.content.slice(offset).trimStart()
        if (head && tail) {
          current.push(sliced(node, head, '~a'))
          flush()
          // The remainder may itself be longer than a page; it is measured
          // again on the next pass rather than assumed to fit.
          const rest = sliced(node, tail, '~b')
          const restHeight = height - remaining
          if (restHeight <= pageHeight) {
            current.push(rest)
            used = restHeight
          } else {
            current.push(rest)
            used = pageHeight
          }
          continue
        }
      }
    }

    // Not splittable, or not worth splitting: start it on a fresh page.
    if (current.length) flush()
    current.push(node)
    used = height
    // A node taller than a whole page owns that page by itself.
    if (height >= pageHeight) flush()
  }

  if (current.length) pages.push(current)
  return pages.length ? pages : [[]]
}
