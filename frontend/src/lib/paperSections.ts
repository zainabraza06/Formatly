import type { ComposeRequest, PaperSpec } from './paperApi'

type Block = Record<string, unknown>

export interface Section {
  /** Index of the level-1 heading that opens the section. */
  start: number
  /** Index after the last block of the section. */
  end: number
  heading: string
  /** Every block in the section, its heading included. */
  blocks: Block[]
  words: number
}

/**
 * The document's top-level sections, read off the blocks.
 *
 * A spec is a flat list of blocks, so a section is simply the run from one
 * level-1 heading to the next. Anything before the first heading (an abstract,
 * say) is not a section and is left alone.
 */
export function sectionsOf(spec: PaperSpec | null): Section[] {
  if (!spec?.blocks?.length) return []
  const blocks = spec.blocks as Block[]

  const starts: number[] = []
  blocks.forEach((b, i) => {
    if (b.type === 'heading' && (b.level ?? 1) === 1) starts.push(i)
  })

  return starts.map((start, n) => {
    const end = n + 1 < starts.length ? starts[n + 1] : blocks.length
    const slice = blocks.slice(start, end)
    return {
      start,
      end,
      heading: String(blocks[start].text ?? 'Untitled section'),
      blocks: slice,
      words: slice.reduce((sum, b) => sum + countWords(b), 0),
    }
  })
}

/** Replace one section's blocks with new ones, leaving the rest untouched. */
export function replaceSection(spec: PaperSpec, section: Section, blocks: Block[]): PaperSpec {
  const next = [...(spec.blocks as Block[])]
  next.splice(section.start, section.end - section.start, ...blocks)
  return { ...spec, blocks: next }
}

/**
 * Ask for one section rather than a whole document.
 *
 * There is no per-section endpoint, so this is the ordinary generate request
 * with the scope stated in the instructions and the rest of the document given
 * as context. What comes back is a small document; `sectionBlocksFrom` takes
 * the part of it that is the section.
 */
export function sectionRequest(
  base: ComposeRequest,
  spec: PaperSpec,
  section: Section,
  note?: string,
): ComposeRequest {
  const outline = sectionsOf(spec).map((s) => s.heading).join(', ')

  return {
    ...base,
    title_hint: section.heading,
    instructions: [
      base.instructions?.trim() || null,
      `Write ONLY the section titled "${section.heading}". Do not write any other section.`,
      `It belongs in a document whose sections are: ${outline}. Do not repeat what the other sections cover.`,
      `Begin with a level-1 heading reading exactly "${section.heading}".`,
      note?.trim() ? `The author asks for this specifically: ${note.trim()}` : null,
    ].filter(Boolean).join('\n'),
  }
}

/**
 * The section out of a one-section response.
 *
 * The model is asked for a single section and usually returns exactly that,
 * but a spec always has room for a title and an abstract — so take from the
 * first level-1 heading onward, and fall back to the whole body when it wrote
 * no heading at all.
 */
export function sectionBlocksFrom(spec: PaperSpec, heading: string): Block[] {
  const blocks = (spec.blocks ?? []) as Block[]
  const first = blocks.findIndex((b) => b.type === 'heading' && (b.level ?? 1) === 1)

  if (first === -1) {
    // No heading came back: keep the section's own heading and use the prose.
    return [{ type: 'heading', level: 1, text: heading }, ...blocks]
  }
  return blocks.slice(first)
}

/**
 * The outline as an instruction. The generator takes plain-language
 * instructions and no structured outline, so a structure the author has fixed
 * is stated in the words the writer already reads.
 */
export function outlineInstruction(headings: string[]): string | null {
  const clean = headings.map((h) => h.trim()).filter(Boolean)
  if (!clean.length) return null
  return [
    'Use exactly these sections, in this order, with these headings:',
    ...clean.map((h, i) => `${i + 1}. ${h}`),
    'Do not add sections that are not on this list, and do not drop any of them.',
  ].join('\n')
}

/** A starting outline for a kind of document, offered rather than imposed. */
export function suggestedOutline(docKind: string): string[] {
  const kind = docKind.toLowerCase()
  if (/paper|thesis|literature|research/.test(kind)) {
    return ['Introduction', 'Related Work', 'Method', 'Results', 'Discussion', 'Conclusion']
  }
  if (/report|case study|white paper/.test(kind)) {
    return ['Executive Summary', 'Background', 'Findings', 'Analysis', 'Recommendations']
  }
  if (/proposal|grant/.test(kind)) {
    return ['Summary', 'Problem', 'Proposed Approach', 'Timeline', 'Budget', 'Expected Outcomes']
  }
  if (/assignment|essay/.test(kind)) {
    return ['Introduction', 'Discussion', 'Conclusion']
  }
  if (/memo|brief/.test(kind)) {
    return ['Purpose', 'Background', 'Recommendation', 'Next Steps']
  }
  return ['Introduction', 'Body', 'Conclusion']
}

function countWords(block: Block): number {
  const text = typeof block.text === 'string' ? block.text : ''
  const items = Array.isArray(block.items) ? block.items.join(' ') : ''
  return `${text} ${items}`.trim().split(/\s+/).filter(Boolean).length
}
