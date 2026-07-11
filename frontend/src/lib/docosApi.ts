import type {
  DocumentGraph,
  GetDocumentResponse,
  GraphDiff,
  ImportResponse,
  VersionInfo,
} from '../types/docos'
import { getToken } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function wsBase(): string {
  return API_URL.replace(/^http/, 'ws')
}

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

export interface DocumentSummary {
  document_id: string
  title: string
  created_at: string
  current_version: string | null
  versions: number
}

export const docosApi = {
  apiUrl: API_URL,

  listDocuments: async (): Promise<DocumentSummary[]> =>
    json(await fetch(`${API_URL}/docos`, { headers: authHeaders() })),

  importDocx: async (file: File): Promise<ImportResponse> => {
    const form = new FormData()
    form.append('file', file)
    return json(await fetch(`${API_URL}/docos/import`, {
      method: 'POST', body: form, headers: authHeaders(),
    }))
  },

  getDocument: async (id: string): Promise<GetDocumentResponse> =>
    json(await fetch(`${API_URL}/docos/${id}`, { headers: authHeaders() })),

  history: async (id: string): Promise<VersionInfo[]> =>
    json(await fetch(`${API_URL}/docos/${id}/history`, { headers: authHeaders() })),

  diff: async (id: string, a: number, b: number): Promise<GraphDiff> =>
    json(await fetch(`${API_URL}/docos/${id}/diff?a=${a}&b=${b}`, { headers: authHeaders() })),

  // REST fallback for running a command (returns collected events + final graph)
  command: async (
    id: string,
    command: string,
  ): Promise<{ ok: boolean; graph?: DocumentGraph; events: any[]; error?: string }> =>
    json(
      await fetch(`${API_URL}/docos/${id}/command`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ command }),
      }),
    ),

  wsUrl: (id: string) => {
    const token = getToken()
    return `${wsBase()}/docos/ws/${id}${token ? `?token=${encodeURIComponent(token)}` : ''}`
  },
}
