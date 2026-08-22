import type {
  AnalyzeChartsResponse,
  ChartSpec,
  GenerateRequest,
  GenerateResponse,
  RecentDocument,
} from '../types/api'
import { getToken } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

/** Every route here is owner-scoped, so the token travels with the request. */
function authHeaders(extra?: HeadersInit): Record<string, string> {
  const token = getToken()
  return {
    ...(extra as Record<string, string> | undefined),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: authHeaders(init?.headers),
  })

  if (!res.ok) {
    throw new Error(await failure(res))
  }

  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    return (await res.json()) as T
  }
  return (await res.text()) as unknown as T
}

/** The server's `detail`, so a failure reads as a sentence rather than as the
 *  raw `{"detail":"..."}` body. */
async function failure(res: Response): Promise<string> {
  try {
    const body = await res.clone().json()
    if (typeof body?.detail === 'string') return body.detail
  } catch {
    /* not JSON — fall through to the text */
  }
  const text = await res.text().catch(() => '')
  return text || `Request failed: ${res.status}`
}

export const api = {
  health: () =>
    http<{ status: string; version: string; exact_preview: boolean }>('/health'),

  generate: (payload: GenerateRequest) =>
    http<GenerateResponse>('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  recentDocuments: () => http<RecentDocument[]>('/paper/recent'),

  // ── Chart endpoints ──────────────────────────────────────────────────────
  analyzeCharts: (documentId: string) =>
    http<AnalyzeChartsResponse>(`/documents/${documentId}/analyze-charts`, {
      method: 'POST',
    }),

  renderChart: (documentId: string, index: number, spec: ChartSpec) =>
    http<{ png_path: string; index: string }>(
      `/documents/${documentId}/charts/${index}/render`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spec),
      },
    ),

  chartImageUrl: (documentId: string, index: number) =>
    `${API_URL}/documents/${documentId}/charts/${index}/image`,

  // ── Exports ──────────────────────────────────────────────────────────────
  // These routes are owner-scoped, and a plain <a href> cannot carry a bearer
  // token — following one lands on `{"detail":"authentication required"}`
  // instead of a file. So fetch the bytes with the token and save them.
  exportDocx: (documentId: string) => download(`/paper/${documentId}/export/docx`),
  exportPdf: (documentId: string) => download(`/paper/${documentId}/export/pdf`),
  exportExcel: (documentId: string) => download(`/documents/${documentId}/export/excel`),
}

/** Fetch an authenticated file and save it under the name the server gave it. */
async function download(path: string): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(await failure(res))

  const disposition = res.headers.get('content-disposition') || ''
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
  const filename = match ? decodeURIComponent(match[1]) : path.split('/').pop() || 'download'

  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
