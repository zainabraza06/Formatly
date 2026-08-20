import { useEffect, useState } from 'react'
import { docosApi } from '../../lib/docosApi'
import type { DocumentGraph } from '../../types/docos'

/** The document as a real layout engine renders it.
 *
 *  The editing canvas re-lays the document out with HTML and CSS, which comes
 *  close but cannot reproduce Word's line breaking or pagination. This asks the
 *  server to render the current graph — edits included — and shows the result,
 *  which is exact and, being a picture of the document, read-only.
 *
 *  It re-renders whenever the graph changes, so switching back after an edit
 *  never shows a stale page. */
export function ExactView({ docId, graph }: { docId: string | null; graph: DocumentGraph | null }) {
  const [url, setUrl] = useState<string | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'unavailable'>('loading')
  const [detail, setDetail] = useState('')

  // The graph identity is the dependency: an edit produces a new graph, which
  // is exactly when this needs rendering again.
  useEffect(() => {
    if (!docId) return
    const run = new AbortController()
    let objectUrl: string | null = null
    setState('loading')

    docosApi.exactPdf(docId, run.signal)
      .then((blob) => {
        if (run.signal.aborted) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
        setState('ready')
      })
      .catch((e) => {
        if (run.signal.aborted) return
        setDetail(e instanceof Error ? e.message : '')
        setState('unavailable')
      })

    return () => {
      run.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [docId, graph])

  if (state === 'loading') {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-muted">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-line border-t-ink" />
        Rendering the exact document…
      </div>
    )
  }

  if (state === 'unavailable' || !url) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <span className="text-sm text-muted">The exact view is unavailable.</span>
        <span className="max-w-md text-xs text-faint">
          {detail.includes('LibreOffice')
            ? 'It needs LibreOffice on the server. The Edit view is unaffected.'
            : detail || 'The document could not be rendered.'}
        </span>
      </div>
    )
  }

  return (
    <iframe
      title="Exact document"
      src={url}
      className="h-full min-h-[70vh] w-full rounded-lg border border-line bg-white"
    />
  )
}
