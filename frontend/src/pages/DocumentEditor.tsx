import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { cn } from '../lib/cn'
import { diffMarks } from '../lib/diffMarks'
import { useDocOS } from '../hooks/useDocOS'
import { useRegisterCommands } from '../context/command-context'
import { useReportError } from '../hooks/useReportError'
import {
  Button, Dropdown, EmptyState, Tabs, Tooltip, useToast,
} from '../components/ui'
import {
  DownloadIcon, EditorIcon, LayersIcon, MoreIcon, SparkIcon, UndoIcon, UploadIcon,
} from '../components/icons'
import { AICommandBar } from '../components/docos/AICommandBar'
import { ChangeReview } from '../components/docos/ChangeReview'
import { ConnectionBadge } from '../components/docos/ConnectionBadge'
import { DocumentOutline } from '../components/docos/DocumentOutline'
import { ExactView } from '../components/docos/ExactView'
import { ExportDialog } from '../components/docos/ExportDialog'
import { GraphCanvas } from '../components/docos/GraphCanvas'
import { VersionTimeline } from '../components/docos/VersionTimeline'
import { UploadDropzone } from '../components/documents/UploadDropzone'

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
  const [searchParams] = useSearchParams()

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
  const noDoc = !doc.docId
  const marks = useMemo(() => diffMarks(doc.diff?.diff), [doc.diff])

  // Open a document passed as ?doc=<id> — from the library, or after an import.
  const requestedId = searchParams.get('doc')
  useEffect(() => {
    if (requestedId && requestedId !== doc.docId) {
      doc.loadDocument(requestedId).catch((e) => report(e, 'open that document'))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedId])

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
  const canvas = noDoc ? (
    <div className="flex h-full items-center justify-center p-4">
      <div className="w-full max-w-md space-y-4">
        <EmptyState
          icon={<EditorIcon className="h-5 w-5" />}
          title="No document open"
          description="Bring in a Word document and tell the assistant what to change — “make all headings consistent”, “reformat the citations”. Every change is versioned, and every one can be undone."
        />
        <UploadDropzone onFile={importFile} busy={importing} />
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

  const sidePanel = (
    <div className="flex h-full min-h-0 flex-col gap-3">
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
    </div>
  )

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[32rem] flex-col gap-3">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold tracking-tight text-ink">
            {doc.title || 'Editor'}
          </h1>
          <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
            {noDoc ? (
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
          <div className="flex shrink-0 flex-wrap items-center gap-2">
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

            <Button
              variant="primary"
              size="sm"
              leadingIcon={<DownloadIcon />}
              onClick={() => setExporting(true)}
            >
              Export
            </Button>

            {/* Everything that is not the main action, one level down. */}
            <Dropdown
              label="More document actions"
              triggerSize="sm"
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

      {/* Hidden control the menu clicks — the dropzone lives in the empty
          state, and this is the same picker for when a document is open. */}
      <input
        id="editor-import"
        type="file"
        accept=".docx"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file) void importFile(file)
        }}
      />

      {/* ── What the assistant just did ──────────────────────────────────── */}
      {doc.review && (
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
      )}

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
            ...PANELS.map((p) => ({ id: p.id, label: p.label })),
          ]}
          className="w-full overflow-x-auto"
        />
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div
        className={cn(
          'grid min-h-0 flex-1 gap-3',
          panelOpen ? 'lg:grid-cols-[minmax(0,1fr)_360px]' : 'lg:grid-cols-[minmax(0,1fr)_auto]',
        )}
      >
        <div
          className={cn(
            'doc-desk min-h-0 overflow-auto rounded-lg border border-line',
            noDoc ? 'p-0' : 'p-3 sm:p-6',
            mobilePanel !== 'document' && 'hidden lg:block',
          )}
        >
          {canvas}
        </div>

        {/* Side panel: a column on a large screen, the selected tab below it. */}
        <aside
          className={cn(
            'min-h-0 flex-col rounded-lg border border-line bg-surface p-3',
            mobilePanel === 'document' ? 'hidden lg:flex' : 'flex',
            !panelOpen && 'lg:hidden',
          )}
        >
          <div className="mb-3 hidden items-center justify-between gap-2 lg:flex">
            <Tabs
              label="Side panel"
              size="sm"
              value={panel}
              onChange={setPanel}
              items={PANELS}
            />
            <Tooltip content="Hide the panel" side="left">
              <Button
                variant="ghost" size="sm" iconOnly
                aria-label="Hide the side panel"
                onClick={() => setPanelOpen(false)}
                leadingIcon={<LayersIcon />}
              />
            </Tooltip>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">{sidePanel}</div>
        </aside>

        {!panelOpen && (
          <div className="hidden lg:flex lg:items-start">
            <Tooltip content="Show the assistant" side="left">
              <Button
                variant="secondary" size="sm" iconOnly
                aria-label="Show the side panel"
                onClick={() => setPanelOpen(true)}
                leadingIcon={<SparkIcon />}
              />
            </Tooltip>
          </div>
        )}
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
    </div>
  )
}
