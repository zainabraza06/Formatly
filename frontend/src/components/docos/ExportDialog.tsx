import { useEffect, useState } from 'react'
import { cn } from '../../lib/cn'
import { docosApi } from '../../lib/docosApi'
import { Button, Modal, Progress, useToast } from '../ui'
import { useReportError } from '../../hooks/useReportError'
import { CheckIcon, DownloadIcon, FileIcon, WarningIcon } from '../icons'

type Format = 'docx' | 'pdf'

const FORMATS: { id: Format; name: string; detail: string }[] = [
  { id: 'docx', name: 'Word (.docx)', detail: 'Editable. Keeps styles, tables, figures and equations.' },
  { id: 'pdf', name: 'PDF', detail: 'Fixed layout, for sending and printing. Rendered on the server.' },
]

/**
 * Export, with the page shown before the file is saved.
 *
 * Exporting used to be two unlabelled buttons that either downloaded a file or
 * raised a browser alert. Here the choice is a choice, the preview is the
 * actual first page of what will be saved, and a failure explains itself
 * inside the dialog instead of in an alert box.
 */
export function ExportDialog({
  open,
  onClose,
  docId,
  title,
  maths,
}: {
  open: boolean
  onClose: () => void
  docId: string
  title: string
  /** Draw LaTeX in the file as mathematics, matching what is on screen. */
  maths: boolean
}) {
  const toast = useToast()
  const report = useReportError()
  const [format, setFormat] = useState<Format>('docx')
  const [saving, setSaving] = useState(false)

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Export document"
      description="Check the page, then save it."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button
            variant="primary"
            loading={saving}
            leadingIcon={<DownloadIcon />}
            onClick={async () => {
              setSaving(true)
              try {
                await docosApi.download(docId, format, maths)
                toast.success(`${format.toUpperCase()} saved`, title)
                onClose()
              } catch (e) {
                report(e, `export the ${format.toUpperCase()}`)
              } finally {
                setSaving(false)
              }
            }}
          >
            Download {format.toUpperCase()}
          </Button>
        </>
      }
    >
      <div className="grid gap-4 sm:grid-cols-[200px_minmax(0,1fr)]">
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium text-ink">Format</legend>
          {FORMATS.map((f) => (
            <label
              key={f.id}
              className={cn(
                'flex cursor-pointer gap-2.5 rounded-md border p-2.5 transition-colors duration-fast',
                format === f.id
                  ? 'border-brand bg-brand-soft'
                  : 'border-line bg-surface hover:border-line-strong',
              )}
            >
              <input
                type="radio"
                name="export-format"
                value={f.id}
                checked={format === f.id}
                onChange={() => setFormat(f.id)}
                className="sr-only"
              />
              <span
                className={cn(
                  'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border',
                  format === f.id ? 'border-brand bg-brand text-brand-fg' : 'border-line-strong',
                )}
                aria-hidden
              >
                {format === f.id && <CheckIcon className="h-3 w-3" />}
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium text-ink">{f.name}</span>
                <span className="mt-0.5 block text-2xs leading-relaxed text-muted">{f.detail}</span>
              </span>
            </label>
          ))}

          {maths && (
            <p className="rounded-md border border-line bg-surface-2 px-2 py-1.5 text-2xs text-muted">
              Equations will be written as mathematics, matching what is on screen.
            </p>
          )}
        </fieldset>

        <FormatPreview docId={docId} open={open} />
      </div>
    </Modal>
  )
}

/**
 * The first page of the document as the server lays it out. Both formats come
 * from the same render, so one preview is honest about both.
 */
function FormatPreview({ docId, open }: { docId: string; open: boolean }) {
  const [url, setUrl] = useState<string | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'unavailable'>('loading')

  useEffect(() => {
    if (!open) return
    const run = new AbortController()
    let objectUrl: string | null = null

    docosApi.exactPdf(docId, run.signal)
      .then((blob) => {
        if (run.signal.aborted) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
        setState('ready')
      })
      .catch(() => setState('unavailable'))

    return () => {
      run.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [docId, open])

  return (
    <div className="min-w-0">
      <p className="mb-2 text-sm font-medium text-ink">Preview</p>

      {state === 'loading' && (
        <div className="space-y-2">
          <Progress value={null} label="Rendering the page" />
          <p className="text-xs text-muted">Laying out the document…</p>
        </div>
      )}

      {state === 'unavailable' && (
        <div className="flex items-start gap-2 rounded-md border border-warning/25 bg-warning-soft p-3 text-xs text-warning">
          <WarningIcon className="mt-px h-4 w-4 shrink-0" />
          <span>
            The page preview needs LibreOffice on the server, which is not available
            here. The DOCX download still works; a PDF export will not.
          </span>
        </div>
      )}

      {state === 'ready' && url && (
        <iframe
          title="Export preview"
          src={`${url}#toolbar=0`}
          className="h-64 w-full rounded-md border border-line bg-white sm:h-80"
        />
      )}

      <p className="mt-2 flex items-center gap-1.5 text-2xs text-faint">
        <FileIcon className="h-3.5 w-3.5" />
        Every edit you have kept is included.
      </p>
    </div>
  )
}
