import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import clsx from 'clsx'
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
  // Clearing everything asks first, in the same two-step way one card does.
  const [askingClearAll, setAskingClearAll] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [cleared, setCleared] = useState<number | null>(null)

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

  const removeEverything = async () => {
    setClearing(true)
    setError(null)
    try {
      const { deleted } = await docosApi.deleteAllDocuments()
      setDocs([])
      // Said out loud: this takes the version history of every upload with it,
      // and a silently emptied page reads the same as one that failed.
      setCleared(deleted)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setClearing(false)
      setAskingClearAll(false)
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
        <div className="flex items-center gap-2">
          {docs.length > 0 && (
            askingClearAll ? (
              // The question replaces the button rather than covering the page:
              // the list it is about stays visible while it is answered.
              <div className="flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/5 px-2 py-1.5">
                <span className="text-xs text-danger">
                  Delete all {docs.length}, with every version?
                </span>
                <button
                  onClick={() => setAskingClearAll(false)}
                  className="rounded-md px-2 py-1 text-xs font-medium text-muted hover:text-ink"
                >
                  Keep
                </button>
                <button
                  onClick={removeEverything}
                  disabled={clearing}
                  className="rounded-md bg-danger px-2 py-1 text-xs font-medium text-white disabled:opacity-60"
                >
                  {clearing ? 'Deleting…' : 'Delete all'}
                </button>
              </div>
            ) : (
              <button
                onClick={() => { setAskingClearAll(true); setCleared(null) }}
                className="rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-muted transition-colors hover:border-danger/40 hover:text-danger"
              >
                Delete all
              </button>
            )
          )}
          <button onClick={() => fileRef.current?.click()} disabled={busy} className={btnPrimary}>
            {busy ? 'Uploading…' : 'Upload DOCX'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">{error}</div>
      )}

      {cleared !== null && (
        <div className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs text-muted">
          Deleted {cleared} {cleared === 1 ? 'upload' : 'uploads'}.
        </div>
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
            <DocumentCard
              key={d.document_id}
              doc={d}
              confirming={confirming === d.document_id}
              deleting={deleting === d.document_id}
              onOpen={() => navigate(`/app/editor?doc=${d.document_id}`)}
              onAskDelete={() => setConfirming(d.document_id)}
              onCancelDelete={() => setConfirming(null)}
              onConfirmDelete={() => remove(d.document_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface CardProps {
  doc: DocumentSummary
  confirming: boolean
  deleting: boolean
  onOpen: () => void
  onAskDelete: () => void
  onCancelDelete: () => void
  onConfirmDelete: () => void
}

/**
 * One upload. Asking to delete *replaces* the card's face rather than covering
 * it — an overlay left the title and date showing through the question, which
 * read as a glitch at the moment the user most needs to be sure what they are
 * deleting. Both faces are the same height, so the grid does not jump.
 */
function DocumentCard({
  doc, confirming, deleting, onOpen, onAskDelete, onCancelDelete, onConfirmDelete,
}: CardProps) {
  const versions = `${doc.versions} version${doc.versions === 1 ? '' : 's'}`

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.18 }}
      className={clsx(
        'group relative h-[104px] overflow-hidden rounded-xl border transition-colors',
        confirming
          ? 'border-danger/40 bg-danger/5'
          : 'border-line bg-surface hover:border-line-strong hover:bg-surface-2',
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        {confirming ? (
          <motion.div
            key="confirm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.14 }}
            className="flex h-full flex-col justify-between gap-2 p-4"
          >
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-ink">
                Delete “{doc.title || 'Untitled'}”?
              </div>
              <p className="mt-0.5 truncate text-[11px] text-muted">
                {versions} and its history, permanently.
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={onCancelDelete}
                disabled={deleting}
                className="rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-surface-2 hover:text-ink disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={onConfirmDelete}
                disabled={deleting}
                autoFocus
                className="rounded-lg bg-danger px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="face"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.14 }}
            className="relative h-full"
          >
            <button
              onClick={onOpen}
              className="flex h-full w-full items-center gap-3 rounded-xl p-4 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-line bg-surface-2 text-base">
                📄
              </span>
              {/* Room on the right so a long title never runs under the trash. */}
              <span className="min-w-0 flex-1 pr-7">
                <span className="block truncate text-sm font-medium text-ink">
                  {doc.title || 'Untitled'}
                </span>
                <span className="mt-1 flex items-center gap-1.5 text-[11px] text-faint">
                  <span>{versions}</span>
                  <span aria-hidden>·</span>
                  <span>{formatDate(doc.created_at)}</span>
                </span>
              </span>
            </button>

            <button
              onClick={onAskDelete}
              aria-label={`Delete ${doc.title || 'Untitled'}`}
              title="Delete upload"
              className="absolute right-2 top-2 rounded-lg p-1.5 text-faint opacity-60 transition hover:bg-danger/10 hover:text-danger focus:outline-none focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-focus group-hover:opacity-100 sm:opacity-0"
            >
              <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.4">
                <path d="M2.5 4h11M6.5 4V2.8h3V4M4.2 4l.6 9.2h6.4l.6-9.2M6.6 6.4v4.6M9.4 6.4v4.6"
                      strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

/** "20 Aug 2026" rather than "8/20/2026" — unambiguous, and the same width
 *  whichever month it is. */
function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}
