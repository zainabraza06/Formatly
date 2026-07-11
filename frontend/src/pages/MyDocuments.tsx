import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GlassCard } from '../components/GlassCard'
import { docosApi, type DocumentSummary } from '../lib/docosApi'

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
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">My Uploads</div>
          <div className="text-xs text-neutral-500">Open any document to edit or revert to a previous version.</div>
        </div>
        <input ref={fileRef} type="file" accept=".docx" hidden onChange={(e) => upload(e.target.files?.[0])} />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="rounded-xl bg-neutral-900 px-4 py-2 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-white dark:text-neutral-950"
        >
          {busy ? 'Uploading…' : 'Upload DOCX'}
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</div>}

      {loading ? (
        <div className="text-sm text-neutral-500">Loading…</div>
      ) : docs.length === 0 ? (
        <GlassCard className="text-center">
          <div className="py-8 text-sm text-neutral-500">
            No uploads yet. Click <span className="font-semibold">Upload DOCX</span> to get started.
          </div>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {docs.map((d) => (
            <motion.button
              key={d.document_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={() => navigate(`/app/editor?doc=${d.document_id}`)}
              className="rounded-2xl border border-white/10 bg-white/10 p-4 text-left shadow-sm backdrop-blur-md transition-colors hover:bg-white/20 dark:bg-white/5"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">📄</span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">{d.title || 'Untitled'}</div>
                  <div className="mt-0.5 text-[11px] text-neutral-500">
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
