import type { GraphNode, Run } from '../../types/docos'

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

/**
 * The largest character offset of `expected` whose text still fits `maxHeight`.
 *
 * The node's box holds more than its text — a hover badge shares it, and the
 * text itself is several elements once a paragraph is formatted in pieces. So
 * the search runs over the marked text element, across every text node in it,
 * and only when those spell out exactly the content being split. Measuring the
 * badge instead is why no paragraph would break across a page: the search ran
 * over the word "Body" and gave up.
 */
function offsetThatFits(element: HTMLElement, maxHeight: number, expected: string): number | null {
  const container = (element.querySelector('[data-node-text]') as HTMLElement | null) ?? element
  // A diff draws words that left as well as words that arrived, so the text on
  // screen is not the text being split; leave those paragraphs whole.
  if (container.textContent !== expected) return null

  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT)
  const pieces: { node: Text; start: number }[] = []
  let total = 0
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n as Text
    pieces.push({ node: text, start: total })
    total += text.data.length
  }
  if (!pieces.length || !total) return null

  const range = document.createRange()
  range.setStart(pieces[0].node, 0)
  const height = (end: number): number => {
    // Which piece the offset lands in, and where inside it.
    let i = pieces.length - 1
    while (i > 0 && pieces[i].start > end) i--
    range.setEnd(pieces[i].node, Math.min(end - pieces[i].start, pieces[i].node.data.length))
    return range.getBoundingClientRect().height
  }

  let lo = 0
  let hi = total
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
  if (best <= 0 || best >= total) return null

  // Break on a word, not mid-word.
  const space = expected.lastIndexOf(' ', best)
  return space > 0 ? space : null
}

/** One line's height, used to keep a stray line off a page on its own. */
function lineHeight(element: HTMLElement): number {
  const parsed = parseFloat(getComputedStyle(element).lineHeight)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 16
}

/** Half of a paragraph, carrying the formatting of the words it kept.
 *
 *  `from`/`to` are offsets into the node's own content, so the pieces are cut
 *  at the same place the text is. Without this a paragraph that broke across a
 *  page came back plain on both sides of the break.
 */
function sliced(node: GraphNode, content: string, suffix: string,
                from: number, to: number): GraphNode {
  const runs = node.runs
  if (!runs?.length || runs.map((r) => r.text).join('') !== node.content) {
    return { ...node, id: `${node.id}${suffix}`, content, runs: [] }
  }

  const kept: Run[] = []
  let at = 0
  for (const run of runs) {
    const start = Math.max(from, at)
    const end = Math.min(to, at + run.text.length)
    if (end > start) kept.push({ text: run.text.slice(start - at, end - at), style: run.style })
    at += run.text.length
  }
  // The halves are trimmed at the break, so the runs are trimmed to match.
  return { ...node, id: `${node.id}${suffix}`, content, runs: trimToText(kept, content) }
}

/** Line the sliced runs back up with the trimmed text, or give up on them. */
function trimToText(runs: Run[], content: string): Run[] {
  const joined = runs.map((r) => r.text).join('')
  if (joined === content) return runs
  const offset = joined.indexOf(content)
  if (offset < 0) return []
  return sliceRunRange(runs, offset, offset + content.length)
}

function sliceRunRange(runs: Run[], from: number, to: number): Run[] {
  const kept: Run[] = []
  let at = 0
  for (const run of runs) {
    const start = Math.max(from, at)
    const end = Math.min(to, at + run.text.length)
    if (end > start) kept.push({ text: run.text.slice(start - at, end - at), style: run.style })
    at += run.text.length
  }
  return kept
}

export interface Measured {
  node: GraphNode
  element: HTMLElement
  /** Height including the gap that follows it. Taken from the distance to the
   *  next sibling rather than the element's own box, so the spacing between
   *  nodes is counted — leaving it out overflows every page by the gaps. */
  height: number
  /** The element's own box, without that gap. What a split half has to fit in:
   *  the gap belongs after the break, not before it. */
  own: number
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

  for (const { node, element, height, own } of measured) {
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
    // The head of a split still carries its own trailing space, so the text it
    // may hold is what is left minus that gap — otherwise the page overflows by
    // the space after the paragraph.
    const budget = remaining - Math.max(0, height - own)
    if (canSplit && budget >= line * MIN_LINES && height - budget >= line * MIN_LINES) {
      const offset = offsetThatFits(element, budget, node.content)
      if (offset) {
        const head = node.content.slice(0, offset).trimEnd()
        const tail = node.content.slice(offset).trimStart()
        if (head && tail) {
          current.push(sliced(node, head, '~a', 0, offset))
          flush()
          // The remainder may itself be longer than a page; it is measured
          // again on the next pass rather than assumed to fit.
          const rest = sliced(node, tail, '~b', offset, node.content.length)
          const restHeight = height - budget
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
