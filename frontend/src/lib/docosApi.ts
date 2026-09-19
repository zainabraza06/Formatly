import type {
  DocumentGraph,
  GetDocumentResponse,
  ImportResponse,
  VersionInfo,
} from '../types/docos'
import { getToken } from './token'
import { getBlob, getJson, request, saveBlob, sendJson, wsUrl } from './http'

export interface DocumentSummary {
  document_id: string
  title: string
  created_at: string
  current_version: string | null
  versions: number
}

export const docosApi = {
  listDocuments: (): Promise<DocumentSummary[]> => getJson('/docos'),

  /** The exported bytes, without saving them. Used by the export preview and
   *  by duplicate, which feeds a document's own export back through import. */
  downloadBlob: (id: string, format: 'docx' | 'pdf', maths = false): Promise<Blob> =>
    getBlob(`/docos/${id}/download.${format}${maths ? '?maths=1' : ''}`),

  /** Save the edited document. The current graph, so every change is in it. */
  /** `maths` is the reader's own toggle: with the equations drawn on screen,
   *  the file should hold equations rather than the LaTeX they were typed as. */
  download: async (id: string, format: 'docx' | 'pdf', maths = false): Promise<void> => {
    const res = await request(`/docos/${id}/download.${format}${maths ? '?maths=1' : ''}`)
    const match = /filename="?([^";]+)"?/i.exec(res.headers.get('content-disposition') || '')
    saveBlob(await res.blob(), match ? match[1] : `document.${format}`)
  },

  /** Delete an upload and its whole version history. Not undoable. */
  deleteDocument: (id: string): Promise<{ deleted: boolean }> =>
    sendJson(`/docos/${id}`, 'DELETE'),

  /** Every upload of the caller's, with all its history. */
  deleteAllDocuments: (): Promise<{ deleted: number }> => sendJson('/docos', 'DELETE'),

  importDocx: async (file: File): Promise<ImportResponse> => {
    const form = new FormData()
    form.append('file', file)
    // No Content-Type: the browser sets it, with the multipart boundary.
    return getJson('/docos/import', { method: 'POST', body: form })
  },

  /** Open a composed document straight from its spec. Going via a rendered
   *  .docx would flatten listings, equations and figures into loose text. */
  importSpec: (spec: unknown, title?: string): Promise<ImportResponse> =>
    sendJson('/docos/import-spec', 'POST', { spec, title }),

  /** The document as LibreOffice lays it out, built from the *current* graph
   *  so it reflects edits rather than the file as it arrived. */
  exactPdf: (id: string, signal?: AbortSignal): Promise<Blob> =>
    getBlob(`/docos/${id}/exact.pdf`, { signal }),

  getDocument: (id: string): Promise<GetDocumentResponse> => getJson(`/docos/${id}`),

  history: (id: string): Promise<VersionInfo[]> => getJson(`/docos/${id}/history`),


  // REST fallback for running a command (returns collected events + final graph)
  command: (
    id: string,
    command: string,
  ): Promise<{ ok: boolean; graph?: DocumentGraph; events: unknown[]; error?: string }> =>
    sendJson(`/docos/${id}/command`, 'POST', { command }),

  wsUrl: (id: string) => {
    const token = getToken()
    return wsUrl(`/docos/ws/${id}${token ? `?token=${encodeURIComponent(token)}` : ''}`)
  },
}

