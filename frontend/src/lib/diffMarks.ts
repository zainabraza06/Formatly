import type { DiffSegment, DiffStyleField, GraphDiff } from '../types/docos'

/** What a compare result says about one node still present in the document. */
export interface DiffMark {
  kind: 'added' | 'changed'
  /** Word-level runs, when the node's text changed. */
  segments?: DiffSegment[]
  /** The style properties that moved, when its formatting changed. */
  styleFields?: DiffStyleField[]
}

/**
 * Index a diff by node id so the page can tint the nodes it names.
 *
 * Removed nodes are left out on purpose: they are not in the graph on screen,
 * so there is nowhere on the page to put them. The timeline lists them instead.
 */
export function diffMarks(diff: GraphDiff | null | undefined): Map<string, DiffMark> {
  const marks = new Map<string, DiffMark>()
  if (!diff) return marks

  for (const node of diff.added) marks.set(node.id, { kind: 'added' })
  for (const change of diff.changed) {
    marks.set(change.id, {
      kind: 'changed',
      segments: change.content?.segments,
      styleFields: change.style?.fields,
    })
  }
  return marks
}
