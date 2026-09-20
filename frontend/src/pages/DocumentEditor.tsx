import { useEffect, useMemo, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { cn } from '../lib/cn'
import { diffMarks } from '../lib/diffMarks'
import { useDocOS } from '../hooks/useDocOS'
import { useRegisterCommands } from '../context/command-context'
import { useReportError } from '../hooks/useReportError'
import { explain } from '../lib/errors'
import {
  Badge, Button, ButtonLink, Dropdown, EmptyState, Spinner, Tabs, Tooltip, useToast,
} from '../components/ui'
import {
  DownloadIcon, LayersIcon, MoreIcon, SparkIcon, UndoIcon, UploadIcon, WarningIcon,
} from '../components/icons'
import { AICommandBar } from '../components/docos/AICommandBar'
import { ChangeReview } from '../components/docos/ChangeReview'
import { ConnectionBadge } from '../components/docos/ConnectionBadge'
import { DocumentOutline } from '../components/docos/DocumentOutline'
import { ExactView } from '../components/docos/ExactView'
import { ExportDialog } from '../components/docos/ExportDialog'
import { GraphCanvas } from '../components/docos/GraphCanvas'
import { VersionTimeline } from '../components/docos/VersionTimeline'
import { DocumentSkeleton } from '../components/docos/DocumentSkeleton'
import { UploadDropzone } from '../components/documents/UploadDropzone'
import { Page } from '../components/layout/Page'

type Panel = 'assistant' | 'structure' | 'history'

const PANELS: { id: Panel; label: string }[] = [
  { id: 'assistant', label: 'Assistant' },
  { id: 'structure', label: 'Structure' },
  { id: 'history', label: 'History' },
]

/**
 * The editor: the document in the middle, the assistant beside it.
 *
 * The old layout was a two-column grid that only existed above 1280px — below
 * that the assistant and the timeline stacked underneath a canvas inside a
 * container that did not scroll, so on a tablet or a phone the command bar was
 * effectively unreachable. Here the side panel is a column on a large screen
 * and a switchable panel below it, and the document is never the thing that
 * gets cut off.
 */
export function DocumentEditor() {
  const doc = useDocOS()
  const toast = useToast()
  const report = useReportError()
  const reduced = useReducedMotion()
  const [searchParams] = useSearchParams()
  const location = useLocation()

  const [view, setView] = useState<'edit' | 'exact'>('edit')
  const [panel, setPanel] = useState<Panel>('assistant')
  const [panelOpen, setPanelOpen] = useState(true)
  const [mobilePanel, setMobilePanel] = useState<'document' | Panel>('document')
  const [exporting, setExporting] = useState(false)
  const [importing, setImporting] = useState<string | null>(null)
  // Off by default: an imported document should look like itself. A paper that
  // types its maths as LaTeX shows the characters it typed, until asked.
  const [renderMaths, setRenderMaths] = useState(false)

  const mathsOn = renderMaths || Boolean(doc.graph?.root?.metadata?.render_maths)
  const running = doc.status === 'running'

  const marks = useMemo(() => diffMarks(doc.diff?.diff), [doc.diff])

  // Open a document passed as ?doc=<id> — from the library, or after an import.
  const requestedId = searchParams.get('doc')
  // The title the library already knew, so the wait can name what is opening
  // rather than saying "a document".
  const requestedTitle = (location.state as { title?: string } | null)?.title
  // The failure is remembered against the document it belongs to, so asking
  // for a different one is not met with the last one's error.
  const [openFailure, setOpenFailure] = useState<{ id: string; detail: string } | null>(null)

  useEffect(() => {
    if (!requestedId || requestedId === doc.docId) return
    doc.loadDocument(requestedId).catch((e) => {
      // Named here as well as in the toast: a toast is gone in four seconds
      // and the screen behind it still has to say what happened.
      setOpenFailure({ id: requestedId, detail: explain(e, 'open that document').detail })
      report(e, 'open that document')
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedId])

  // Opening covers the whole gap between asking for a document and having it:
  // the fetch itself, and the moment before the request has even started, when
  // all we have is the id in the address. Without the second half the editor
  // flashes its empty state on the way in.
  const openError = openFailure?.id === requestedId ? openFailure.detail : null
  const opening = !openError && (doc.opening || Boolean(requestedId && requestedId !== doc.docId))
  const noDoc = !doc.docId && !opening

  const importFile = async (file: File) => {
    setImporting('Reading the document…')
    try {
      await doc.importFile(file)
      toast.success('Document imported', 'The assistant is reading it through now.')
    } catch (e) {
      report(e, 'import that file', () => void importFile(file))
    } finally {
      setImporting(null)
    }
  }

  useRegisterCommands(() => [
    { id: 'doc-export', group: 'Document', label: 'Export this document',
      icon: <DownloadIcon />, disabled: noDoc, run: () => setExporting(true) },
    { id: 'doc-undo', group: 'Document', label: 'Undo the last change',
      icon: <UndoIcon />, disabled: noDoc || running, run: doc.undo },
    { id: 'doc-redo', group: 'Document', label: 'Redo',
      disabled: noDoc || running, run: doc.redo },
    { id: 'doc-ask', group: 'Document', label: 'Tell the assistant what to change',
      icon: <SparkIcon />, disabled: noDoc,
      run: () => {
        setPanel('assistant')
        setMobilePanel('assistant')
        setPanelOpen(true)
        window.setTimeout(() => document.getElementById('ai-command')?.focus(), 50)
      } },
    { id: 'doc-maths', group: 'Document',
      label: renderMaths ? 'Stop drawing LaTeX as mathematics' : 'Draw LaTeX as mathematics',
      disabled: noDoc, run: () => setRenderMaths((m) => !m) },
  ], [noDoc, running, renderMaths, doc.undo, doc.redo])

  // ── the document, whichever way it is being shown ────────────────────────
  const canvas = opening ? (
    <DocumentSkeleton title={requestedTitle || doc.title} />
  ) : openError ? (
    <div className="flex h-full items-center justify-center p-6">
      <EmptyState
        tone="error"
        icon={<WarningIcon className="h-5 w-5" />}
        title="That document could not be opened"
        description={openError}
        action={
          <Button
            variant="primary"
            onClick={() => {
              if (!requestedId) return
              setOpenFailure(null)
              doc.loadDocument(requestedId).catch((e) => {
                setOpenFailure({ id: requestedId, detail: explain(e, 'open that document').detail })
              })
            }}
          >
            Try again
          </Button>
        }
        secondaryAction={
          <ButtonLink to="/app" variant="secondary">Back to documents</ButtonLink>
        }
      />
    </div>
  ) : noDoc ? (
    // One empty state, not two: the dropzone is the action, and saying "no
    // document open" above a box that says "drop a document here" was the same
    // sentence twice.
    <div className="flex h-full items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <UploadDropzone onFile={importFile} busy={importing}>
          Open a Word document
        </UploadDropzone>
        <p className="mt-3 text-xs leading-relaxed text-muted">
          Then tell the assistant what to change — “make all headings consistent”,
          “reformat the citations”. Every change is versioned, and every one can be
          undone.
        </p>
      </div>
    </div>
  ) : view === 'exact' ? (
    <ExactView docId={doc.docId} graph={doc.graph} />
  ) : (
    <GraphCanvas
      graph={doc.graph}
      selectedIds={doc.selectedIds}
      activeId={doc.activeId}
      removingIds={doc.removingIds}
      marks={marks}
      focusId={doc.focusId}
      renderMaths={mathsOn}
    />
  )

  // The panel's three faces are one surface changing, not three surfaces
  // taking turns: the tab indicator slides, so the content should not blink.
  const sidePanel = (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={panel}
        initial={reduced ? { opacity: 0 } : { opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        className="flex h-full min-h-0 flex-col gap-3"
      >
      {panel === 'assistant' && (
        <AICommandBar
          panel={doc.panel}
          running={running}
          disabled={noDoc}
          onRun={doc.runCommand}
        />
      )}
      {panel === 'structure' && (
        <DocumentOutline
          graph={doc.graph}
          focusId={doc.focusId}
          onFocus={doc.focusNode}
        />
      )}
      {panel === 'history' && (
        <VersionTimeline
          versions={doc.versions}
          diff={doc.diff}
          disabled={noDoc || running}
          onUndo={doc.undo}
          onRedo={doc.redo}
          onRewind={doc.rewind}
          onRestore={doc.restore}
          onCompare={doc.compare}
          onCloseDiff={doc.clearDiff}
        />
      )}
      </motion.div>
    </AnimatePresence>
  )

  return (
    <Page fill className="h-[calc(100vh-7rem)] min-h-[34rem] !gap-3">
      {/* ── Document header: what this is, and what you can do to it ─────── */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl text-ink">
            {doc.title || requestedTitle || 'Editor'}
          </h1>
          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
            {opening ? (
              <span className="flex items-center gap-1.5">
                <Spinner size="sm" />
                Opening…
              </span>
            ) : noDoc ? (
              <span>Open a Word document to edit it with AI</span>
            ) : (
              <>
                <ConnectionBadge state={doc.connection} />
                <span>{doc.versions.length} {doc.versions.length === 1 ? 'version' : 'versions'}</span>
              </>
            )}
          </div>
        </div>

        {!noDoc && (
          <div className="flex shrink-0 items-center gap-2">
            <Button
              variant="primary"
              size="md"
              disabled={opening}
              leadingIcon={<DownloadIcon />}
              onClick={() => setExporting(true)}
            >
              Export
            </Button>

            <Dropdown
              label="More document actions"
              triggerSize="md"
              triggerIcon={<MoreIcon />}
              items={[
                {
                  id: 'maths',
                  label: renderMaths ? 'Stop drawing LaTeX as maths' : 'Draw LaTeX as maths',
                  icon: <SparkIcon />,
                  onSelect: () => setRenderMaths((m) => !m),
                },
                {
                  id: 'undo', label: 'Undo the last change', icon: <UndoIcon />,
                  disabled: running, onSelect: doc.undo,
                },
                {
                  id: 'import', label: 'Import another document', icon: <UploadIcon />,
                  onSelect: () => document.getElementById('editor-import')?.click(),
                },
              ]}
            />
          </div>
        )}
      </div>

      {/* Hidden control the menu clicks — the dropzone is the way in when no
          document is open, and this is the way in when one already is. */}
      <input
        id="editor-import"
        type="file"
        accept=".docx"
        aria-label="Import another Word document"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file) void importFile(file)
        }}
      />

      {/* ── What the assistant just did ──────────────────────────────────── */}
      <AnimatePresence>
        {doc.review && (
          <motion.div
            key="review"
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: -8, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: -8 }}
            transition={{ type: 'spring', stiffness: 420, damping: 34, mass: 0.7 }}
          >
            <ChangeReview
              review={doc.review}
              busy={running}
              onKeep={doc.acceptChanges}
              onUndo={() => {
                doc.rejectChanges()
                toast.info('Change undone', 'The document is back as it was.')
              }}
              onShowChanges={() => {
                doc.showChanges()
                setPanel('history')
                setMobilePanel('history')
                setPanelOpen(true)
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Small screens: one thing at a time ───────────────────────────── */}
      <div className="lg:hidden">
        <Tabs
          label="Show the document or a panel"
          value={mobilePanel}
          onChange={(id) => {
            setMobilePanel(id)
            if (id !== 'document') setPanel(id)
          }}
          items={[
            { id: 'document', label: 'Document' },
            ...PANELS.map((pnl) => ({ id: pnl.id, label: pnl.label })),
          ]}
          className="w-full overflow-x-auto"
        />
      </div>

      {/* ── The workspace: one frame, two columns inside it ──────────────── */}
      <div
        className={cn(
          'grid min-h-0 flex-1 overflow-hidden rounded-lg border border-line bg-surface',
          panelOpen ? 'lg:grid-cols-[minmax(0,1fr)_23rem]' : 'lg:grid-cols-1',
        )}
      >
        {/* The document, with its own toolbar above it */}
        <section
          className={cn(
            'flex min-h-0 flex-col',
            mobilePanel !== 'document' && 'hidden lg:flex',
          )}
        >
          {(!noDoc || opening) && (
            <div className="flex h-10 shrink-0 items-center justify-between gap-2 border-b border-line px-2">
              {/* How the document is drawn belongs to the document, not to the
                  page header two rows above it. */}
              <Tabs
                label="How to show the document"
                size="sm"
                value={view}
                onChange={setView}
                items={[
                  { id: 'edit', label: 'Edit' },
                  { id: 'exact', label: 'Exact' },
                ]}
              />

              <div className="flex items-center gap-1">
                {mathsOn && <Badge tone="brand">maths drawn</Badge>}
                {!panelOpen && (
                  <Tooltip content="Show the assistant" side="left">
                    <Button
                      variant="ghost" size="sm" iconOnly
                      aria-label="Show the side panel"
                      onClick={() => setPanelOpen(true)}
                      leadingIcon={<SparkIcon />}
                    />
                  </Tooltip>
                )}
              </div>
            </div>
          )}

          <div
            tabIndex={noDoc ? undefined : 0}
            role={noDoc ? undefined : 'region'}
            aria-label={noDoc ? undefined : `${doc.title || 'Document'} — page view`}
            className={cn(
              'min-h-0 flex-1 overflow-auto',
              noDoc ? 'bg-surface' : 'doc-desk p-4 sm:p-6',
            )}
          >
            {canvas}
          </div>
        </section>

        {/* The assistant, sharing the frame rather than floating beside it */}
        <aside
          className={cn(
            'min-h-0 flex-col border-line lg:border-l',
            mobilePanel === 'document' ? 'hidden lg:flex' : 'flex',
            !panelOpen && 'lg:hidden',
          )}
        >
          <div className="hidden h-10 shrink-0 items-center justify-between gap-2 border-b border-line px-2 lg:flex">
            <Tabs label="Side panel" size="sm" value={panel} onChange={setPanel} items={PANELS} />
            <Tooltip content="Hide the panel" side="left">
              <Button
                variant="ghost" size="sm" iconOnly
                aria-label="Hide the side panel"
                onClick={() => setPanelOpen(false)}
                leadingIcon={<LayersIcon />}
              />
            </Tooltip>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden p-3">{sidePanel}</div>
        </aside>
      </div>

      {doc.docId && (
        <ExportDialog
          open={exporting}
          onClose={() => setExporting(false)}
          docId={doc.docId}
          title={doc.title}
          maths={mathsOn}
        />
      )}
    </Page>
  )
}
