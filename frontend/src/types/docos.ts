// Types mirroring the DocOS backend (app/docos).

export type NodeType =
  | 'document' | 'paragraph' | 'heading' | 'subheading' | 'body'
  | 'image' | 'figure' | 'caption' | 'table' | 'table_row' | 'table_cell'
  | 'horizontal_rule' | 'page_break' | 'header' | 'footer' | 'reference' | 'footnote'

export interface Style {
  font_family?: string | null
  font_size?: number | null
  bold?: boolean | null
  italic?: boolean | null
  underline?: boolean | null
  color?: string | null
  highlight?: string | null
  alignment?: 'left' | 'center' | 'right' | 'justify' | null
  /** Inline only: a citation marker or a formula, raised or lowered. */
  vertical_align?: 'superscript' | 'subscript' | null
}

/** A stretch of a paragraph formatted as one piece. `style` holds only what the
 *  run states for itself; anything null it inherits from the paragraph. */
export interface Run {
  text: string
  style: Style
}

export interface GraphNode {
  id: string
  type: NodeType
  content: string
  style: Style
  metadata: Record<string, unknown>
  children: GraphNode[]
  /** Empty when the whole node is formatted alike — see `inlineRuns`. */
  runs?: Run[]
}

/**
 * A node's text as formatted pieces, always safe to render.
 *
 * Mirrors `Node.inline_runs()` on the server, including its safety check: the
 * content is the text of record, so runs that no longer spell it out (a rewrite
 * replaced the words) are ignored rather than drawn over the new text.
 */
export function inlineRuns(node: GraphNode): Run[] {
  const runs = node.runs
  if (runs?.length && runs.map((r) => r.text).join('') === node.content) return runs
  return node.content ? [{ text: node.content, style: {} }] : []
}

export interface PageGeometry {
  width_in: number
  height_in: number
  landscape?: boolean
  margin: { top: number; right: number; bottom: number; left: number }
  count?: number    // exact page count when repaginated via LibreOffice
  exact?: boolean
  // The document's own typeface and size, so the sheet is laid out in the font
  // the file actually uses rather than the viewer's default.
  default_font?: string
  default_size_pt?: number
}

export interface DocumentGraph {
  root: GraphNode
  title: string
}

const DEFAULT_PAGE: PageGeometry = {
  width_in: 8.5, height_in: 11, margin: { top: 1, right: 1, bottom: 1, left: 1 },
}

export function pageGeometry(graph: DocumentGraph | null): PageGeometry {
  const p = graph?.root?.metadata?.page as PageGeometry | undefined
  return p && p.width_in && p.height_in ? p : DEFAULT_PAGE
}

export interface VersionInfo {
  id: string
  parent_id: string | null
  seq: number
  timestamp: string
  user: string
  label: string
  is_checkpoint: boolean
  is_current: boolean
}

export interface ImportResponse {
  document_id: string
  title: string
  version: VersionInfo
  graph: DocumentGraph
}

export interface GetDocumentResponse {
  document_id: string
  title: string
  current_version: string | null
  graph: DocumentGraph
}

// ── streamed events ─────────────────────────────────────────────────────────
export type DocOSEventName =
  | 'command_parsed' | 'batch_started' | 'batch_finished' | 'batch_failed'
  | 'selection_started' | 'selection_item' | 'selection_finished'
  | 'format_started' | 'format_progress' | 'format_finished'
  | 'delete_started' | 'delete_item' | 'delete_finished'
  | 'insert_started' | 'insert_item' | 'insert_finished'
  | 'move_started' | 'move_item' | 'move_finished'
  | 'replace_started' | 'replace_item' | 'replace_finished'
  | 'action_error' | 'version_committed' | 'version_changed'
  // The assistant reading a long document, a page at a time.
  | 'rewrite_progress' | 'rewrite_finished' | 'rewrite_fallback' | 'command_noop'
  // Reading a document through once, when it first arrives.
  | 'reading_started' | 'reading_progress' | 'reading_finished' | 'section_located'
  | 'control_noop' | 'compare_result' | 'error'

/**
 * Everything an event can carry, as the server sends it.
 *
 * One type with optional fields rather than a union per event name: the
 * payload genuinely is a loose bag on the wire, and this at least names every
 * key the client reads and says what type it arrives as — which `any` did not,
 * and which is what let `p.total` be read where the server sends `p.count`.
 */
export interface DocOSPayload {
  /** The node an event is about, and the set a step covers. */
  id?: string
  ids?: string[]
  /** What was asked for, in the planner's words. */
  target?: string
  /** Sizes and tallies. `total` is what a step will do; `count` what it did. */
  total?: number
  count?: number
  index?: number
  /** Formatting carried by a format_progress. */
  style?: Style
  highlight?: string
  /** The plan, before any of it has run. */
  actions?: { type: string; target?: string }[]
  provider?: string
  source?: string
  fell_back_because?: string
  /** Reading the document through, page by page. */
  page?: number
  of?: number
  pass?: number
  edited?: number
  read?: number
  /** Where the assistant decided an instruction pointed. */
  heading?: string
  /** Outcomes. */
  summary?: string
  reason?: string
  warnings?: string[]
  error?: string
  detail?: string
  /** Version control: the two ends of a comparison, and its result. */
  a?: number
  b?: number
  diff?: GraphDiff
  op?: string
}

export interface DocOSEvent {
  event: DocOSEventName
  payload: DocOSPayload
}

export interface DiffNode {
  id: string
  type: string
  content: string
  truncated?: boolean
}

/** One run of words shared by, or unique to, one side of a text change. */
export interface DiffSegment {
  op: 'equal' | 'insert' | 'delete'
  text: string
}

export interface DiffContentChange {
  before: string
  after: string
  segments: DiffSegment[]
  truncated?: boolean
}

export interface DiffStyleField {
  field: string
  before: unknown
  after: unknown
}

export interface DiffStyleChange {
  before: Record<string, unknown>
  after: Record<string, unknown>
  fields: DiffStyleField[]
}

export interface DiffChange {
  id: string
  type: string
  content?: DiffContentChange
  style?: DiffStyleChange
}

export interface DiffSummary {
  added: number
  removed: number
  changed: number
  text_changed: number
  style_changed: number
  words_added: number
  words_removed: number
}

export interface GraphDiff {
  added: DiffNode[]
  removed: DiffNode[]
  changed: DiffChange[]
  summary?: DiffSummary
}
