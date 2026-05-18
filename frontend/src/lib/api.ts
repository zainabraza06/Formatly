import type {
  ChatRequest,
  ChatResponse,
  Draft,
  GenerateRequest,
  GenerateResponse,
  RecentDocument,
  TemplateAnalyzeResponse,
  Tone,
} from '../types/api'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
    },
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Request failed: ${res.status}`)
  }

  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    return (await res.json()) as T
  }
  return (await res.text()) as unknown as T
}

export const api = {
  health: () => http<{ status: string }>('/health'),

  generate: (payload: GenerateRequest) =>
    http<GenerateResponse>('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  recentDocuments: () => http<RecentDocument[]>('/documents/recent'),

  getDraft: (documentId: string) => http<Draft>(`/documents/${documentId}/draft`),

  saveDraft: (documentId: string, draft: Draft) =>
    http<{ status: string }>(`/documents/${documentId}/draft`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    }),

  rewriteSection: (documentId: string, sectionId: string, tone: Tone) =>
    http<{ status: string; section: { id: string; heading: string; content: string } }>(
      `/documents/${documentId}/sections/${sectionId}/rewrite`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tone),
      },
    ),

  uploadTemplate: async (file: File) => {
    const form = new FormData()
    form.append('file', file)

    const res = await fetch(`${API_URL}/templates/upload`, {
      method: 'POST',
      body: form,
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `Upload failed: ${res.status}`)
    }

    return (await res.json()) as TemplateAnalyzeResponse
  },

  analyzeTemplate: (templateId: string) =>
    http<TemplateAnalyzeResponse>(`/templates/${templateId}/analyze`),

  exportDocxUrl: (documentId: string) => `${API_URL}/documents/${documentId}/export/docx`,
  exportPdfUrl: (documentId: string) => `${API_URL}/documents/${documentId}/export/pdf`,

  chat: (payload: ChatRequest) =>
    http<ChatResponse>('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
}
