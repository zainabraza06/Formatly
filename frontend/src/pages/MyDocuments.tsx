import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { docosApi, type DocumentSummary } from '../lib/docosApi'
import { btnPrimary } from '../lib/ui'

export function MyDocuments() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [docs, setDocs] = useState<DocumentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // The card awaiting a second click, so deleting a whole history takes two.
  const [confirming, setConfirming] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    docosApi.listDocuments()
      .then(setDocs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const remove = async (id: string) => {
    setDeleting(id)
    setError(null)
    try {
      await docosApi.deleteDocument(id)
      // Drop it locally rather than refetching: the list is already correct.
      setDocs((current) => current.filter((d) => d.document_id !== id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setDeleting(null)
      setConfirming(null)
    }
  }

  const upload = async (file: File | undefined) => {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const res = await docosApi.importDocx(file)
      navigate(`/app/editor?doc=${res.document_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">My Uploads</h1>
          <p className="mt-0.5 text-sm text-muted">Open any document to edit or revert to a previous version.</p>
        </div>
        <input ref={fileRef} type="file" accept=".docx" hidden onChange={(e) => upload(e.target.files?.[0])} />
        <button onClick={() => fileRef.current?.click()} disabled={busy} className={btnPrimary}>
          {busy ? 'Uploading…' : 'Upload DOCX'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">{error}</div>
      )}

      {loading ? (
        <div className="text-sm text-muted">Loading…</div>
      ) : docs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line-strong py-16 text-center">
          <div className="text-sm text-muted">
            No uploads yet. Click <span className="font-medium text-ink">Upload DOCX</span> to get started.
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {docs.map((d) => (
            <motion.div
              key={d.document_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="group relative rounded-xl border border-line bg-surface transition-colors hover:bg-surface-2"
            >
              {/* The card opens the document; the delete control sits outside
                  that button rather than inside it — a button cannot nest. */}
              <button
                onClick={() => navigate(`/app/editor?doc=${d.document_id}`)}
                disabled={deleting === d.document_id}
                className="flex w-full items-start gap-3 p-4 text-left disabled:opacity-50"
              >
                <span className="text-xl">📄</span>
                <div className="min-w-0 pr-6">
                  <div className="truncate text-sm font-medium text-ink">{d.title || 'Untitled'}</div>
                  <div className="mt-0.5 text-[11px] text-faint">
                    {d.versions} version{d.versions === 1 ? '' : 's'} · {new Date(d.created_at).toLocaleDateString()}
                  </div>
                </div>
              </button>

              {confirming === d.document_id ? (
                <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 rounded-b-xl border-t border-danger/30 bg-danger/10 px-3 py-2">
                  <span className="text-[11px] text-danger">
                    Delete this and all {d.versions} version{d.versions === 1 ? '' : 's'}?
                  </span>
                  <span className="flex gap-1">
                    <button
                      onClick={() => setConfirming(null)}
                      className="rounded-lg border border-line bg-surface px-2 py-0.5 text-[11px] text-muted hover:bg-surface-2"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => remove(d.document_id)}
                      disabled={deleting === d.document_id}
                      className="rounded-lg bg-danger px-2 py-0.5 text-[11px] font-medium text-white disabled:opacity-50"
                    >
                      {deleting === d.document_id ? 'Deleting…' : 'Delete'}
                    </button>
                  </span>
                </div>
              ) : (
                <button
                  onClick={() => setConfirming(d.document_id)}
                  aria-label={`Delete ${d.title || 'Untitled'}`}
                  title="Delete upload"
                  className="absolute right-2 top-2 rounded-lg p-1.5 text-faint opacity-0 transition hover:bg-danger/10 hover:text-danger focus:opacity-100 group-hover:opacity-100"
                >
                  <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2.5 4h11M6 4V2.5h4V4M4 4l.5 9.5h7L12 4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
