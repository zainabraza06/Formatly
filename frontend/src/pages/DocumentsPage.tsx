import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { docosApi } from '../lib/docosApi'
import {
  duplicateUpload, loadDocuments, openGeneratedInEditor, searchDocuments, sortDocuments,
  SORT_LABELS, type DocumentItem, type DocumentSource, type SortKey,
} from '../lib/documents'
import { useRegisterCommands } from '../context/command-context'
import { useReportError } from '../hooks/useReportError'
import {
  Button, ButtonLink, ConfirmModal, EmptyState, Input, Select, Tabs, useToast,
} from '../components/ui'
import { ComposeIcon, DocumentsIcon, PlusIcon, SearchIcon } from '../components/icons'
import { DocumentCard, DocumentCardSkeleton } from '../components/documents/DocumentCard'
import { UploadDropzone } from '../components/documents/UploadDropzone'

type Filter = 'all' | DocumentSource

/**
 * The library: everything the account has, whether the generator wrote it or
 * somebody uploaded it, searchable and sortable, with the actions on each
 * document in one menu rather than spread over three screens.
 */
export function DocumentsPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const report = useReportError()

  const [items, setItems] = useState<DocumentItem[]>([])
  const [failures, setFailures] = useState<{ source: DocumentSource; message: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [sort, setSort] = useState<SortKey>('newest')
  const [busyId, setBusyId] = useState<{ id: string; what: string } | null>(null)
  const [uploading, setUploading] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<DocumentItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  const refresh = useCallback(async () => {
    const result = await loadDocuments()
    setItems(result.items)
    setFailures(result.failures)
    setLoading(false)
  }, [])

  useEffect(() => {
    let alive = true
    loadDocuments().then((r) => {
      if (!alive) return
      setItems(r.items)
      setFailures(r.failures)
      setLoading(false)
    })
    return () => { alive = false }
  }, [])

  // ── actions ───────────────────────────────────────────────────────────────

  const upload = async (file: File) => {
    setUploading('Reading the document…')
    try {
      const res = await docosApi.importDocx(file)
      toast.success('Document imported', 'Opening it in the editor.')
      navigate(`/app/editor?doc=${encodeURIComponent(res.document_id)}`)
    } catch (e) {
      report(e, 'import that file', () => void upload(file))
      setUploading(null)
    }
  }

  const open = async (doc: DocumentItem) => {
    if (doc.source === 'upload') {
      navigate(`/app/editor?doc=${encodeURIComponent(doc.id)}`)
      return
    }
    // A generated paper becomes editable by importing its own export, so what
    // opens is a copy — said out loud rather than discovered later.
    setBusyId({ id: doc.id, what: 'Preparing a copy…' })
    try {
      const id = await openGeneratedInEditor(doc)
      toast.success('Copy opened in the editor', 'The generated paper itself is unchanged.')
      navigate(`/app/editor?doc=${encodeURIComponent(id)}`)
    } catch (e) {
      report(e, 'open that document', () => void open(doc))
    } finally {
      setBusyId(null)
    }
  }

  const exportDoc = async (doc: DocumentItem, format: 'docx' | 'pdf') => {
    setBusyId({ id: doc.id, what: `Preparing ${format.toUpperCase()}…` })
    const id = toast.loading(`Preparing the ${format.toUpperCase()}…`, doc.title)
    try {
      if (doc.source === 'upload') await docosApi.download(doc.id, format)
      else if (format === 'docx') await api.exportDocx(doc.id, doc.title)
      else await api.exportPdf(doc.id, doc.title)
      toast.toast({ id, tone: 'success', title: `${format.toUpperCase()} downloaded`, description: doc.title })
    } catch (e) {
      toast.dismiss(id)
      report(e, `export the ${format.toUpperCase()}`, () => void exportDoc(doc, format))
    } finally {
      setBusyId(null)
    }
  }

  const duplicate = async (doc: DocumentItem) => {
    setBusyId({ id: doc.id, what: 'Duplicating…' })
    try {
      await duplicateUpload(doc)
      await refresh()
      toast.success('Duplicated', `A copy of “${doc.title}” is in your library.`)
    } catch (e) {
      report(e, 'duplicate that document', () => void duplicate(doc))
    } finally {
      setBusyId(null)
    }
  }

  const remove = async () => {
    const doc = confirmDelete
    if (!doc) return
    setDeleting(true)
    try {
      if (doc.source === 'upload') await docosApi.deleteDocument(doc.id)
      else await api.deletePaper(doc.id)
      setItems((all) => all.filter((d) => d.id !== doc.id))
      toast.success(
        'Deleted',
        doc.source === 'upload'
          ? `“${doc.title}” and its version history are gone.`
          : `“${doc.title}” is gone.`,
      )
      setConfirmDelete(null)
    } catch (e) {
      report(e, 'delete that document')
    } finally {
      setDeleting(false)
    }
  }

  // ── commands for this screen ──────────────────────────────────────────────

  useRegisterCommands(() => [
    {
      id: 'new-document', group: 'Create', label: 'New document',
      icon: <ComposeIcon />, shortcut: ['N'], keywords: 'generate write paper',
      run: () => navigate('/app/compose'),
    },
    {
      id: 'focus-search', group: 'Documents', label: 'Search your documents',
      icon: <SearchIcon />, keywords: 'find filter',
      run: () => document.getElementById('document-search')?.focus(),
    },
    ...(['newest', 'oldest', 'title', 'versions'] as SortKey[]).map((key) => ({
      id: `sort-${key}`, group: 'Documents', label: `Sort: ${SORT_LABELS[key]}`,
      run: () => setSort(key),
    })),
  ], [navigate])

  // "N" for a new document, the way every document product does it — but never
  // while someone is typing into a field.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const el = e.target as HTMLElement | null
      if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return
      if (el?.isContentEditable) return
      if (e.key.toLowerCase() === 'n') {
        e.preventDefault()
        navigate('/app/compose')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate])

  // ── derived ───────────────────────────────────────────────────────────────

  const counts = useMemo(() => ({
    all: items.length,
    generated: items.filter((d) => d.source === 'generated').length,
    upload: items.filter((d) => d.source === 'upload').length,
  }), [items])

  const visible = useMemo(() => {
    const byFilter = filter === 'all' ? items : items.filter((d) => d.source === filter)
    return sortDocuments(searchDocuments(byFilter, query), sort)
  }, [items, filter, query, sort])

  const nothingAtAll = !loading && items.length === 0
  const nothingMatches = !loading && items.length > 0 && visible.length === 0

  return (
    <div className="space-y-5">
      {/* ── Header: one primary action ─────────────────────────────────── */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Documents</h1>
          <p className="mt-1 text-sm text-muted">
            Everything you have generated or uploaded, in one place.
          </p>
        </div>
        <ButtonLink to="/app/compose" variant="primary" leadingIcon={<PlusIcon />}>
          New document
        </ButtonLink>
      </div>

      {failures.map((f) => (
        <div
          key={f.source}
          role="alert"
          className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-md border border-warning/25 bg-warning-soft px-3 py-2 text-xs text-warning"
        >
          <span className="min-w-0 flex-1">
            <strong className="font-medium">
              {f.source === 'upload' ? 'Your uploads' : 'Your generated papers'} could not be loaded.
            </strong>{' '}
            {f.message}
          </span>
          <Button variant="secondary" size="sm" onClick={() => { setLoading(true); void refresh() }}>
            Try again
          </Button>
        </div>
      ))}

      {/* ── Controls ───────────────────────────────────────────────────── */}
      {!nothingAtAll && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Input
            id="document-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title…"
            aria-label="Search your documents"
            leadingIcon={<SearchIcon />}
            className="sm:max-w-xs"
          />

          <Tabs
            label="Filter documents by where they came from"
            value={filter}
            onChange={setFilter}
            items={[
              { id: 'all', label: 'All', count: counts.all },
              { id: 'generated', label: 'Generated', count: counts.generated },
              { id: 'upload', label: 'Uploads', count: counts.upload },
            ]}
          />

          <div className="sm:ml-auto">
            <label htmlFor="document-sort" className="sr-only">Sort documents</label>
            <Select
              id="document-sort"
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="sm:w-44"
            >
              {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
                <option key={key} value={key}>{SORT_LABELS[key]}</option>
              ))}
            </Select>
          </div>
        </div>
      )}

      {/* ── The library ────────────────────────────────────────────────── */}
      {loading ? (
        <div aria-busy="true" aria-label="Loading your documents" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => <DocumentCardSkeleton key={i} />)}
        </div>
      ) : nothingAtAll ? (
        <div className="space-y-4">
          <EmptyState
            icon={<DocumentsIcon className="h-5 w-5" />}
            title="No documents yet"
            description="Describe what you need and Formatly writes it, formatted and ready to export — or bring a Word document you already have."
            action={
              <ButtonLink to="/app/compose" variant="primary" leadingIcon={<ComposeIcon />}>
                Generate a document
              </ButtonLink>
            }
          />
          <UploadDropzone onFile={upload} busy={uploading} compact>
            …or drop a Word document to edit it with AI
          </UploadDropzone>
        </div>
      ) : nothingMatches ? (
        <EmptyState
          icon={<SearchIcon className="h-5 w-5" />}
          title={`Nothing matches “${query}”`}
          description="Try fewer words, or clear the filter to see everything."
          action={
            <Button variant="secondary" onClick={() => { setQuery(''); setFilter('all') }}>
              Clear search and filters
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {visible.map((doc) => (
              <DocumentCard
                key={`${doc.source}:${doc.id}`}
                doc={doc}
                busy={busyId?.id === doc.id ? busyId.what : null}
                onOpen={() => open(doc)}
                onExport={(format) => exportDoc(doc, format)}
                onDuplicate={doc.source === 'upload' ? () => duplicate(doc) : undefined}
                onDelete={() => setConfirmDelete(doc)}
              />
            ))}
          </div>

          <UploadDropzone onFile={upload} busy={uploading} compact className="pt-1">
            Drop a Word document to edit it with AI
          </UploadDropzone>
        </>
      )}

      <ConfirmModal
        open={Boolean(confirmDelete)}
        onClose={() => setConfirmDelete(null)}
        onConfirm={remove}
        busy={deleting}
        title={`Delete “${confirmDelete?.title ?? ''}”?`}
        description={
          confirmDelete?.source === 'upload'
            ? `This deletes the document and all ${confirmDelete.versions ?? 0} of its versions. It cannot be undone.`
            : 'This deletes the generated paper. It cannot be undone — a paper has no version history to fall back on.'
        }
        confirmLabel={confirmDelete?.source === 'upload' ? 'Delete document' : 'Delete paper'}
      />
    </div>
  )
}

