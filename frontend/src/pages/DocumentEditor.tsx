import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { GlassCard } from '../components/GlassCard'
import { AIPanel } from '../components/docos/AIPanel'
import { GraphCanvas } from '../components/docos/GraphCanvas'
import { VersionTimeline } from '../components/docos/VersionTimeline'
import { useDocOS } from '../hooks/useDocOS'
import { btnPrimary } from '../lib/ui'

export function DocumentEditor() {
  const doc = useDocOS()
  const [searchParams] = useSearchParams()
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
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
        <div className="flex gap-2">
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
          ) : (
            <GraphCanvas
              graph={doc.graph}
              selectedIds={doc.selectedIds}
              activeId={doc.activeId}
              removingIds={doc.removingIds}
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
            />
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
