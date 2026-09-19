import { downloadFile, getBlob, getJson, safeFilename, sendJson } from './http'
import type { RecentDocument } from '../types/api'

/**
 * The paper half of the API: documents the generator wrote, and their exports.
 *
 * The editor's half lives in docosApi, and the generator's writing routes in
 * paperApi. All three share the plumbing in http.ts.
 */
export const api = {
  /** The caller's own generated papers, newest first. */
  recentDocuments: () => getJson<RecentDocument[]>('/paper/recent'),

  /** Delete a generated paper. Not undoable: a paper is its spec, and there is
   *  no version history behind it the way there is for an imported document. */
  deletePaper: (documentId: string) =>
    sendJson<{ deleted: boolean }>(`/paper/${documentId}`, 'DELETE'),

  exportDocx: (documentId: string, title?: string) =>
    downloadFile(`/paper/${documentId}/export/docx`, safeFilename(title, documentId, 'docx')),

  exportPdf: (documentId: string, title?: string) =>
    downloadFile(`/paper/${documentId}/export/pdf`, safeFilename(title, documentId, 'pdf')),

  /** The exported bytes without saving them — for opening a generated paper in
   *  the editor, which imports its own .docx. */
  exportBlob: (path: string) => getBlob(path),
}
