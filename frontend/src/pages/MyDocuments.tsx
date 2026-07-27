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

  const load = () => {
    setLoading(true)
    docosApi.listDocuments()
      .then(setDocs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

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
            <motion.button
              key={d.document_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={() => navigate(`/app/editor?doc=${d.document_id}`)}
              className="rounded-xl border border-line bg-surface p-4 text-left transition-colors hover:bg-surface-2"
            >
              <div className="flex items-start gap-3">
                <span className="text-xl">📄</span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-ink">{d.title || 'Untitled'}</div>
                  <div className="mt-0.5 text-[11px] text-faint">
                    {d.versions} version{d.versions === 1 ? '' : 's'} · {new Date(d.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </motion.button>
          ))}
        </div>
      )}
    </div>
  )
}
