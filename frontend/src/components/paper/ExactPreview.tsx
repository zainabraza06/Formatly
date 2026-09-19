import { useEffect, useState } from 'react'
import { isAbort, paperApi, type PaperSpec } from '../../lib/paperApi'
import { Progress } from '../ui'
import { DocumentPreview } from './DocumentPreview'

type State = 'loading' | 'ready' | 'unavailable'

/**
 * The document as it will actually be: the real .docx, rendered to a PDF by
 * the same engine that produces the download.
 *
 * Mounted fresh for each version of the spec — the caller keys it — so it
 * never shows the previous document while the current one renders. When the
 * server has no LibreOffice to render with, it falls back to the HTML reading
 * view and says which one is on screen.
 */
export function ExactPreview({
  spec,
  mode,
  className,
}: {
  spec: PaperSpec
  /** `reading` skips the render entirely and shows the HTML view. */
  mode: 'exact' | 'reading'
  className?: string
}) {
  const [state, setState] = useState<State>('loading')
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (mode !== 'exact') return
    const run = new AbortController()
    let objectUrl: string | null = null

    paperApi.previewPdf(spec, undefined, run.signal)
      .then((blob) => {
        if (run.signal.aborted) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
        setState('ready')
      })
      .catch((e) => {
        if (!isAbort(e)) setState('unavailable')
      })

    return () => {
      run.abort()
      // Aborted renders are abandoned: nobody is waiting for a preview of a
      // document that has already been replaced.
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [spec, mode])

  if (mode === 'exact' && state === 'ready' && url) {
    return (
      <iframe
        title="Exact document preview"
        src={url}
        className={className ?? 'h-[60vh] w-full rounded-lg border border-line bg-white sm:h-[75vh]'}
      />
    )
  }

  return (
    <div className="space-y-2">
      {mode === 'exact' && state === 'loading' && (
        <Progress value={null} label="Rendering the document" />
      )}
      {mode === 'exact' && state === 'unavailable' && (
        <p className="rounded-md border border-warning/25 bg-warning-soft px-3 py-2 text-xs text-warning">
          Showing the reading view — the exact page render needs LibreOffice on the
          server. The DOCX download is unaffected.
        </p>
      )}
      <div className="doc-desk max-h-[75vh] overflow-auto rounded-lg border border-line p-3 sm:p-6">
        <DocumentPreview spec={spec} />
      </div>
    </div>
  )
}
