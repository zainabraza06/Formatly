import { useRef, useState, type ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { Button, Progress } from '../ui'
import { UploadIcon, WarningIcon } from '../icons'

const MAX_MB = 25

/**
 * Drop a .docx, or click to pick one. It validates before anything is sent —
 * the wrong file type and an over-large file both fail in the browser, where
 * the answer is immediate, rather than after an upload.
 */
export function UploadDropzone({
  onFile,
  busy,
  compact,
  children,
  className,
}: {
  onFile: (file: File) => void
  /** Text for what is happening, e.g. "Reading the document…". */
  busy?: string | null
  compact?: boolean
  children?: ReactNode
  className?: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const accept = (file: File | undefined) => {
    setError(null)
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.docx')) {
      setError(`${file.name} is not a .docx file. Word documents only — save it as .docx and try again.`)
      return
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`${file.name} is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is ${MAX_MB} MB.`)
      return
    }
    onFile(file)
  }

  return (
    <div className={className}>
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true) }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setOver(false)
          accept(e.dataTransfer.files?.[0])
        }}
        className={cn(
          'flex flex-col items-center justify-center rounded-lg border border-dashed text-center transition-colors duration-fast',
          compact ? 'gap-2 px-4 py-6' : 'gap-3 px-6 py-10',
          over ? 'border-brand bg-brand-soft' : 'border-line bg-surface-2/40',
          busy && 'pointer-events-none opacity-70',
        )}
      >
        <span
          className={cn(
            'flex items-center justify-center rounded-lg border bg-surface',
            compact ? 'h-9 w-9' : 'h-11 w-11',
            over ? 'border-brand/30 text-brand-ink' : 'border-line text-faint',
          )}
          aria-hidden
        >
          <UploadIcon className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
        </span>

        {busy ? (
          <div className="w-full max-w-xs space-y-2">
            <p className="text-sm font-medium text-ink">{busy}</p>
            <Progress value={null} label={busy} />
          </div>
        ) : (
          <>
            <div>
              <p className="text-sm font-medium text-ink">
                {children ?? 'Drop a Word document here'}
              </p>
              <p className="mt-0.5 text-xs text-muted">
                .docx up to {MAX_MB} MB — it opens in the editor, with its formatting intact
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={() => inputRef.current?.click()}>
              Choose a file
            </Button>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".docx"
          className="sr-only"
          onChange={(e) => {
            accept(e.target.files?.[0])
            // Cleared so picking the same file twice fires change both times.
            e.target.value = ''
          }}
        />
      </div>

      {error && (
        <p role="alert" className="mt-2 flex items-start gap-1.5 text-xs text-danger">
          <WarningIcon className="mt-px h-3.5 w-3.5 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}
