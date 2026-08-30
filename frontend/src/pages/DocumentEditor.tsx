import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { GlassCard } from '../components/GlassCard'
import { AIPanel } from '../components/docos/AIPanel'
import { ExactView } from '../components/docos/ExactView'
import { GraphCanvas } from '../components/docos/GraphCanvas'
import { VersionTimeline } from '../components/docos/VersionTimeline'
import { useDocOS } from '../hooks/useDocOS'
import { diffMarks } from '../lib/diffMarks'
import { btnPrimary } from '../lib/ui'

export function DocumentEditor() {
  const doc = useDocOS()
  const [searchParams] = useSearchParams()
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [view, setView] = useState<'edit' | 'exact'>('edit')
  // Off by default: an imported document should look like itself. A paper that
  // types its maths as LaTeX shows the characters it typed, until asked.
  const [renderMaths, setRenderMaths] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // open a document passed via ?doc=<id> (from My Uploads / after import)
  const requestedId = searchParams.get('doc')
  useEffect(() => {
    if (requestedId && requestedId !== doc.docId) {
      doc.loadDocument(requestedId).catch((e) =>
        setError(e instanceof Error ? e.message : 'Failed to open document'),
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedId])

  const running = doc.status === 'running'
  const noDoc = !doc.docId
  // The open compare result, indexed by node id so the page can tint what it names.
  const marks = useMemo(() => diffMarks(doc.diff?.diff), [doc.diff])

  const handleFile = async (file: File | undefined) => {
    if (!file) return
    setError(null)
    try {
      await doc.importFile(file)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'import failed')
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-4">
      {/* header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            {doc.title || 'Document OS'}
          </h1>
          <div className="mt-0.5 text-sm text-muted">
            {noDoc ? 'Upload a DOCX to start editing with AI' : (
              <span className="flex items-center gap-1.5">
                <span className={clsx('h-1.5 w-1.5 rounded-full', doc.connected ? 'bg-emerald-500' : 'bg-faint')} />
                {doc.connected ? 'live' : 'offline'} · {doc.versions.length} versions
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* The editor lays out with HTML and CSS, which comes close but is not
              the document. Exact hands the current graph to a real layout engine
              and shows what it produces — accurate, and read-only for it. */}
          {!noDoc && (
            <div className="flex rounded-lg border border-line bg-surface p-0.5 text-xs">
              {(['edit', 'exact'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setView(m)}
                  className={clsx(
                    'rounded-md px-2.5 py-1 font-medium transition-colors',
                    view === m ? 'bg-surface-2 text-ink' : 'text-muted hover:text-ink',
                  )}
                >
                  {m === 'edit' ? 'Edit' : 'Exact'}
                </button>
              ))}
            </div>
          )}
          {!noDoc && (
            <button
              onClick={() => setRenderMaths((on) => !on)}
              title="Draw LaTeX typed into the text as mathematics. Equations the
document stores as equations are always drawn."
              className={clsx(
                'rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors',
                renderMaths
                  ? 'border-line-strong bg-surface-2 text-ink'
                  : 'border-line bg-surface text-muted hover:text-ink',
              )}
            >
              ∑ Maths
            </button>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".docx"
            hidden
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          <button onClick={() => fileRef.current?.click()} className={btnPrimary}>
            {noDoc ? 'Import DOCX' : 'Import another'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">{error}</div>
      )}

      {/* body: editor + side panels */}
      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden xl:grid-cols-[minmax(0,1fr)_360px]">
        {/* editor canvas */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragOver(false)
            void handleFile(e.dataTransfer.files?.[0])
          }}
          className={clsx(
            // Word-like gray canvas around the page — kept light in both themes
            'overflow-auto rounded-xl border border-line bg-neutral-200/70 p-6 dark:bg-neutral-800/60',
            dragOver && 'ring-2 ring-focus/50',
          )}
        >
          {noDoc ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-faint">
              <span className="text-4xl">📄</span>
              <div className="text-sm">Drag & drop a .docx here, or click Import</div>
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
              renderMaths={renderMaths}
            />
          )}
        </div>

        {/* side panels */}
        <div className="grid grid-rows-2 gap-4 overflow-hidden">
          <GlassCard className="overflow-auto">
            <AIPanel panel={doc.panel} running={running} disabled={noDoc} onRun={doc.runCommand} />
          </GlassCard>
          <GlassCard className="overflow-hidden">
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
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
