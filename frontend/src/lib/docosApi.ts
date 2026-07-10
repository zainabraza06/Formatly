import type {
  DocumentGraph,
  GetDocumentResponse,
  GraphDiff,
  ImportResponse,
  VersionInfo,
} from '../types/docos'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function wsBase(): string {
  return API_URL.replace(/^http/, 'ws')
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Request failed: ${res.status}`)
  }
  return (await res.json()) as T
}

export const docosApi = {
  apiUrl: API_URL,

  importDocx: async (file: File): Promise<ImportResponse> => {
    const form = new FormData()
    form.append('file', file)
    return json(await fetch(`${API_URL}/docos/import`, { method: 'POST', body: form }))
  },

  getDocument: async (id: string): Promise<GetDocumentResponse> =>
    json(await fetch(`${API_URL}/docos/${id}`)),

  history: async (id: string): Promise<VersionInfo[]> =>
    json(await fetch(`${API_URL}/docos/${id}/history`)),

  diff: async (id: string, a: number, b: number): Promise<GraphDiff> =>
    json(await fetch(`${API_URL}/docos/${id}/diff?a=${a}&b=${b}`)),

  // REST fallback for running a command (returns collected events + final graph)
  command: async (
    id: string,
    command: string,
  ): Promise<{ ok: boolean; graph?: DocumentGraph; events: any[]; error?: string }> =>
    json(
      await fetch(`${API_URL}/docos/${id}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      }),
    ),

  wsUrl: (id: string) => `${wsBase()}/docos/ws/${id}`,
}
