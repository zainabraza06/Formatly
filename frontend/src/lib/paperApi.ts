import { getToken } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken()
  return { ...(extra || {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = ''
    try {
      detail = (await res.clone().json()).detail
    } catch {
      detail = await res.text().catch(() => '')
    }
    throw new Error(detail || `Request failed: ${res.status}`)
  }
  return (await res.json()) as T
}

async function blob(res: Response): Promise<Blob> {
  if (!res.ok) {
    let detail = ''
    try {
      detail = (await res.clone().json()).detail
    } catch {
      detail = await res.text().catch(() => '')
    }
    throw new Error(detail || `Request failed: ${res.status}`)
  }
  return await res.blob()
}

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

export interface PaperSpec {
  meta: {
    title: string
    authors: { name: string; affiliation?: string; email?: string }[]
    abstract: string
    keywords: string[]
    style: string
    page: Record<string, unknown>
  }
  blocks: Record<string, any>[]
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

export const paperApi = {
  styles: async (): Promise<StyleSummary[]> =>
    json(await fetch(`${API_URL}/paper/styles`, { headers: authHeaders() })),

  getStyle: async (id: string): Promise<Record<string, any>> =>
    json(await fetch(`${API_URL}/paper/styles/${id}`, { headers: authHeaders() })),

  createStyle: async (sheet: Record<string, any>): Promise<Record<string, any>> =>
    json(await fetch(`${API_URL}/paper/styles`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(sheet),
    })),


  deleteStyle: async (id: string): Promise<{ deleted: boolean }> =>
    json(await fetch(`${API_URL}/paper/styles/${id}`, {
      method: 'DELETE', headers: authHeaders(),
    })),

  // `signal` lets the caller abandon a run. Generation can take minutes, so the
  // user needs a way out that does not mean reloading the page.
  generate: async (req: ComposeRequest, signal?: AbortSignal): Promise<{ provider: string; spec: PaperSpec }> =>
    json(await fetch(`${API_URL}/paper/generate`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
      signal,
    })),

  renderSpec: async (spec: PaperSpec, style?: string, signal?: AbortSignal): Promise<Blob> =>
    blob(await fetch(`${API_URL}/paper/render${style ? `?style=${encodeURIComponent(style)}` : ''}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(spec),
      signal,
    })),

  // Pixel-exact preview: the real DOCX rendered to PDF. May 503 if LibreOffice
  // is unavailable, in which case the caller falls back to the HTML view.
  previewPdf: async (spec: PaperSpec, style?: string, signal?: AbortSignal): Promise<Blob> =>
    blob(await fetch(`${API_URL}/paper/preview${style ? `?style=${encodeURIComponent(style)}` : ''}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(spec),
      signal,
    })),

  compose: async (req: ComposeRequest, signal?: AbortSignal): Promise<Blob> =>
    blob(await fetch(`${API_URL}/paper/compose`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
      signal,
    })),
}

export function isAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === 'AbortError'
}

export function downloadBlob(b: Blob, filename: string): void {
  const url = URL.createObjectURL(b)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
