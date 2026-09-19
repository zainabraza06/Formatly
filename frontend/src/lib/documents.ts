import { api } from './api'
import { docosApi } from './docosApi'
import { explain } from './errors'
import type { RecentDocument } from '../types/api'

/**
 * One document, whichever half of the product made it.
 *
 * The app kept two lists in two places — papers the generator wrote, and .docx
 * files people uploaded to edit — and showed them on three different screens.
 * They are one library here; `source` is what the screens vary on.
 */
export interface DocumentItem {
  id: string
  title: string
  createdAt: string | null
  source: DocumentSource
  /** Uploads only: how many versions the editor has recorded. */
  versions?: number
  /** Generated papers only: the style it was written in. */
  stylePreset?: string
}

export type DocumentSource = 'generated' | 'upload'

export interface DocumentsResult {
  items: DocumentItem[]
  /** Named so a half-loaded library says which half is missing rather than
   *  pretending the documents were never there. */
  failures: { source: DocumentSource; message: string }[]
}

export async function loadDocuments(): Promise<DocumentsResult> {
  const [uploads, generated] = await Promise.allSettled([
    docosApi.listDocuments(),
    api.recentDocuments(),
  ])

  const items: DocumentItem[] = []
  const failures: DocumentsResult['failures'] = []

  if (uploads.status === 'fulfilled') {
    items.push(...uploads.value.map((d): DocumentItem => ({
      id: d.document_id,
      title: d.title || 'Untitled',
      createdAt: d.created_at ?? null,
      source: 'upload',
      versions: d.versions,
    })))
  } else {
    failures.push({ source: 'upload', message: messageOf(uploads.reason) })
  }

  if (generated.status === 'fulfilled') {
    items.push(...generated.value.map((d: RecentDocument & { created_at?: string }): DocumentItem => ({
      id: d.document_id,
      title: d.title || 'Untitled',
      createdAt: d.created_at ?? null,
      source: 'generated',
      stylePreset: d.style_preset,
    })))
  } else {
    failures.push({ source: 'generated', message: messageOf(generated.reason) })
  }

  return { items, failures }
}

export type SortKey = 'newest' | 'oldest' | 'title' | 'versions'

export const SORT_LABELS: Record<SortKey, string> = {
  newest: 'Newest first',
  oldest: 'Oldest first',
  title: 'Title A–Z',
  versions: 'Most edited',
}

export function sortDocuments(items: DocumentItem[], key: SortKey): DocumentItem[] {
  const copy = [...items]
  switch (key) {
    case 'oldest':
      return copy.sort((a, b) => time(a) - time(b))
    case 'title':
      return copy.sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' }))
    case 'versions':
      return copy.sort((a, b) => (b.versions ?? 0) - (a.versions ?? 0) || time(b) - time(a))
    case 'newest':
    default:
      return copy.sort((a, b) => time(b) - time(a))
  }
}

/** Matches on any word of the query, in any order, ignoring case. */
export function searchDocuments(items: DocumentItem[], query: string): DocumentItem[] {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return items
  return items.filter((d) => {
    const haystack = `${d.title} ${d.stylePreset ?? ''} ${d.source}`.toLowerCase()
    return words.every((w) => haystack.includes(w))
  })
}

/**
 * Copy a document by sending its own export back through import.
 *
 * There is no duplicate endpoint, and inventing one would change the API. A
 * .docx round trip is what the product already promises is lossless — it is
 * the format every export and every upload uses — so the copy is made out of
 * the same bytes the owner would have downloaded.
 */
export async function duplicateUpload(item: DocumentItem): Promise<string> {
  const blob = await docosApi.downloadBlob(item.id, 'docx')
  const file = new File([blob], `${item.title || 'document'} copy.docx`, { type: blob.type })
  const res = await docosApi.importDocx(file)
  return res.document_id
}

/**
 * Open a generated paper in the editor by importing its own .docx export.
 * The editor works on documents, and a generated paper only becomes one when
 * it is rendered — so this is a copy, and the screen says so.
 */
export async function openGeneratedInEditor(item: DocumentItem): Promise<string> {
  const blob = await api.exportBlob(`/paper/${item.id}/export/docx`)
  const file = new File([blob], `${item.title || 'document'}.docx`, { type: blob.type })
  const res = await docosApi.importDocx(file)
  return res.document_id
}

export function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''

  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

function time(d: DocumentItem): number {
  const t = d.createdAt ? new Date(d.createdAt).getTime() : NaN
  return Number.isNaN(t) ? 0 : t
}

function messageOf(reason: unknown): string {
  const { title, detail } = explain(reason, 'load your documents')
  return `${title}. ${detail}`
}
