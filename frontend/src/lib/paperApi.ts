import { getBlob, getJson, sendJson } from './http'

export { isAbort } from './errors'

export interface StyleSummary {
  id: string
  name: string
  columns: string
  builtin: string          // "true" | "false" (server sends strings)
  heading_scheme: string
  table_borders: string
}

export interface VisualizationNote {
  data: string
  kind: string
  rationale: string
}

/** A block is a tagged union on the server; the editor only ever reads `type`,
 *  `level` and `text` off one, and passes the rest back untouched. */
export type PaperBlock = Record<string, unknown>

export interface PaperSpec {
  meta: {
    title: string
    authors: { name: string; affiliation?: string; email?: string }[]
    abstract: string
    keywords: string[]
    style: string
    page: Record<string, unknown>
  }
  blocks: PaperBlock[]
  references: string[]
  visualization_plan: VisualizationNote[]
  resolved: boolean
}

/** Any extra material under the user's own label — measurements, a transcript,
 *  survey responses, source code, citations. Nothing domain-specific. */
export interface Attachment {
  label: string
  content: string
}

export type Depth = 'brief' | 'standard'

export interface ComposeRequest {
  raw_text: string
  style: string
  doc_kind: string
  depth?: Depth
  attachments?: Attachment[]
  reference_example?: string | null
  instructions?: string | null
  title_hint?: string | null
  authors?: { name: string; affiliation?: string; email?: string }[]
}

export interface RefinedInstructions {
  provider: string
  improved: string
  changes: string[]
  questions: string[]
}

export const paperApi = {
  /** Refine a loose instruction into one the writer can act on. `previous` and
   *  `feedback` make a retry a correction rather than another roll of the dice. */
  refineInstructions: (
    body: {
      instructions: string
      raw_text?: string
      doc_kind?: string
      style?: string
      previous?: string | null
      feedback?: string | null
    },
    signal?: AbortSignal,
  ): Promise<RefinedInstructions> =>
    sendJson('/paper/instructions/refine', 'POST', body, { signal }),

  styles: (): Promise<StyleSummary[]> => getJson('/paper/styles'),

  // `signal` lets the caller abandon a run. Generation can take minutes, so the
  // user needs a way out that does not mean reloading the page.
  generate: (req: ComposeRequest, signal?: AbortSignal): Promise<{ provider: string; spec: PaperSpec }> =>
    sendJson('/paper/generate', 'POST', req, { signal }),

  renderSpec: (spec: PaperSpec, style?: string, signal?: AbortSignal): Promise<Blob> =>
    getBlob(`/paper/render${styleQuery(style)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
      signal,
    }),

  // Pixel-exact preview: the real DOCX rendered to PDF. May 503 if LibreOffice
  // is unavailable, in which case the caller falls back to the HTML view.
  previewPdf: (spec: PaperSpec, style?: string, signal?: AbortSignal): Promise<Blob> =>
    getBlob(`/paper/preview${styleQuery(style)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
      signal,
    }),

  compose: (req: ComposeRequest, signal?: AbortSignal): Promise<Blob> =>
    getBlob('/paper/compose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
      signal,
    }),
}

function styleQuery(style?: string): string {
  return style ? `?style=${encodeURIComponent(style)}` : ''
}

export { saveBlob as downloadBlob } from './http'
