import type {
  AnalyzeChartsResponse,
  ChartSpec,
  GenerateRequest,
  GenerateResponse,
  RecentDocument,
} from '../types/api'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(init?.headers || {}) },
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

  // ── Export URLs ──────────────────────────────────────────────────────────
  exportDocxUrl:  (documentId: string) => `${API_URL}/paper/${documentId}/export/docx`,
  exportPdfUrl:   (documentId: string) => `${API_URL}/paper/${documentId}/export/pdf`,
  exportExcelUrl: (documentId: string) => `${API_URL}/documents/${documentId}/export/excel`
}
