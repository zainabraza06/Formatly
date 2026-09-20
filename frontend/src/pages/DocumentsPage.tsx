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
  Button, ButtonLink, ConfirmModal, Dropdown, EmptyState, Input, Select, Tabs, useToast,
} from '../components/ui'
import {
  ComposeIcon, DocumentsIcon, LayersIcon, MoreIcon, PlusIcon, SearchIcon, TrashIcon, UploadIcon,
} from '../components/icons'
import { DocumentCard, DocumentCardSkeleton } from '../components/documents/DocumentCard'
import { DocumentTable, DocumentTableSkeleton } from '../components/documents/DocumentTable'
import { UploadDropzone } from '../components/documents/UploadDropzone'

type Filter = 'all' | DocumentSource

const VIEW_KEY = 'formatly.library.view'

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
  // A list is the right default for something that grows to hundreds of rows;
  // the grid stays for anyone who prefers it, and the choice is remembered.
  const [view, setView] = useState<'list' | 'grid'>(
    () => (localStorage.getItem(VIEW_KEY) === 'grid' ? 'grid' : 'list'),
  )
  const [busyId, setBusyId] = useState<{ id: string; what: string } | null>(null)
  const [uploading, setUploading] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<DocumentItem | null>(null)
  const [deleting, setDeleting] = useState(false)
  // Emptying the whole library is a separate question, asked separately.
  const [confirmClear, setConfirmClear] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [dragging, setDragging] = useState(false)

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

  /**
   * Delete every upload, with all their versions. Generated papers are left
   * alone: they are a different list, deleted one at a time, and sweeping them
   * up in a button labelled for uploads is how people lose work they meant to
   * keep.
   */
  const clearUploads = async () => {
    setClearing(true)
    try {
      const { deleted } = await docosApi.deleteAllDocuments()
      setItems((all) => all.filter((d) => d.source !== 'upload'))
      toast.success(
        `Deleted ${deleted} ${deleted === 1 ? 'upload' : 'uploads'}`,
        'Their version histories went with them.',
      )
      setConfirmClear(false)
    } catch (e) {
      report(e, 'delete your uploads')
    } finally {
      setClearing(false)
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
    {
      id: 'toggle-view', group: 'Documents',
      label: view === 'list' ? 'Show the library as a grid' : 'Show the library as a list',
      icon: <LayersIcon />,
      run: () => setView((v) => (v === 'list' ? 'grid' : 'list')),
    },
    ...(['newest', 'oldest', 'title', 'versions'] as SortKey[]).map((key) => ({
      id: `sort-${key}`, group: 'Documents', label: `Sort: ${SORT_LABELS[key]}`,
      run: () => setSort(key),
    })),
  ], [navigate, view])

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
    <div
      className="relative space-y-4"
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={(e) => { if (e.currentTarget === e.target) setDragging(false) }}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer.files?.[0]
        if (file) void upload(file)
      }}
    >
      {dragging && (
        <div className="pointer-events-none fixed inset-0 z-40 flex items-center justify-center bg-brand/5 backdrop-blur-[1px]">
          <p className="rounded-lg border-2 border-dashed border-brand bg-surface px-6 py-4 text-sm font-medium text-brand-ink shadow-lg">
            Drop to open it in the editor
          </p>
        </div>
      )}
      {/* ── Header: one primary action ─────────────────────────────────── */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl text-ink">Documents</h1>
          <p className="mt-1 text-sm text-muted">
            {loading
              ? 'Everything you have generated or uploaded, in one place.'
              : visible.length === items.length
                ? `${items.length} ${items.length === 1 ? 'document' : 'documents'}`
                : `${visible.length} of ${items.length} documents`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ButtonLink to="/app/compose" variant="primary" leadingIcon={<PlusIcon />}>
            New document
          </ButtonLink>

          <Dropdown
            label="More library actions"
            triggerIcon={<MoreIcon />}
            items={[
              {
                id: 'upload',
                label: 'Upload a Word document',
                icon: <UploadIcon />,
                onSelect: () => document.getElementById('library-upload')?.click(),
              },
              {
                id: 'clear',
                label: 'Delete all uploads…',
                icon: <TrashIcon />,
                destructive: true,
                disabled: counts.upload === 0,
                onSelect: () => setConfirmClear(true),
              },
            ]}
          />
        </div>
      </div>

      {/* The menu's picker. The dropzone below is the usual way in; this is
          for anyone who went looking in a menu instead. */}
      <input
        id="library-upload"
        type="file"
        accept=".docx"
        aria-label="Upload a Word document"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file) void upload(file)
        }}
      />

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
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
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
            <div className="flex items-center gap-2">
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

              <Tabs
                label="How to show the library"
                size="sm"
                value={view}
                onChange={(next) => {
                  setView(next)
                  try { localStorage.setItem(VIEW_KEY, next) } catch { /* private mode */ }
                }}
                items={[
                  { id: 'list', label: 'List' },
                  { id: 'grid', label: 'Grid' },
                ]}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── The library ────────────────────────────────────────────────── */}
      {loading ? (
        <div aria-busy="true" aria-label="Loading your documents">
          {view === 'list' ? (
            <DocumentTableSkeleton />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {Array.from({ length: 6 }).map((_, i) => <DocumentCardSkeleton key={i} />)}
            </div>
          )}
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
          {view === 'list' ? (
            <DocumentTable
              documents={visible}
              busyId={busyId}
              sort={sort}
              onSort={setSort}
              onOpen={open}
              onExport={exportDoc}
              onDuplicate={duplicate}
              onDelete={setConfirmDelete}
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {visible.map((doc, index) => (
                <DocumentCard
                  key={`${doc.source}:${doc.id}`}
                  doc={doc}
                  index={index}
                  busy={busyId?.id === doc.id ? busyId.what : null}
                  onOpen={() => open(doc)}
                  onExport={(format) => exportDoc(doc, format)}
                  onDuplicate={doc.source === 'upload' ? () => duplicate(doc) : undefined}
                  onDelete={() => setConfirmDelete(doc)}
                />
              ))}
            </div>
          )}

          {/* A quiet strip once there are documents: the library is what this
              screen is for, and a dropzone the size of the list said otherwise.
              The whole page still accepts a drop. */}
          <p className="flex items-center justify-center gap-1.5 py-1 text-xs text-faint">
            <UploadIcon className="h-3.5 w-3.5" />
            Drop a Word document anywhere to edit it with AI, or
            <button
              type="button"
              onClick={() => document.getElementById('library-upload')?.click()}
              className="rounded-sm font-medium text-brand-ink hover:underline"
            >
              choose a file
            </button>
          </p>
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

      <ConfirmModal
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        onConfirm={clearUploads}
        busy={clearing}
        title={`Delete all ${counts.upload} uploads?`}
        description={
          'Every document you have uploaded, and every version of each one, permanently. '
          + 'Generated papers are not affected.'
        }
        confirmLabel="Delete all uploads"
      />
    </div>
  )
}

