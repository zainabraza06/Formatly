import { useMemo, useRef, useState } from 'react'
import clsx from 'clsx'
import { motion } from 'framer-motion'
import { LoadingDots } from './LoadingDots'
import type { TemplateAnalyzeResponse } from '../types/api'

export function UploadDropzone({
  onUpload,
  uploaded,
}: {
  onUpload: (file: File) => Promise<TemplateAnalyzeResponse>
  uploaded?: TemplateAnalyzeResponse | null
}) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const accept = useMemo(() => '.docx,.pdf,.png,.jpg,.jpeg,.webp', [])

  async function handleFile(file: File) {
    setError(null)
    setBusy(true)
    try {
      await onUpload(file)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <motion.button
        type="button"
        whileHover={{ y: -1 }}
        whileTap={{ scale: 0.99 }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setIsDragging(false)
          const file = e.dataTransfer.files?.[0]
          if (file) void handleFile(file)
        }}
        className={clsx(
          'w-full rounded-2xl border border-dashed p-4 text-left transition',
          'bg-white/10 dark:bg-white/5 backdrop-blur-md',
          isDragging ? 'border-sky-400/60 ring-1 ring-sky-400/40' : 'border-white/20',
        )}
        disabled={busy}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              Drag & drop a template
            </div>
            <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
              Upload DOCX/PDF/images. DOCX gives best style cloning.
            </div>
          </div>
          <div className="text-xs text-neutral-700 dark:text-neutral-300">
            {busy ? (
              <span className="inline-flex items-center gap-2">
                Analyzing <LoadingDots />
              </span>
            ) : (
              'Upload'
            )}
          </div>
        </div>

        {uploaded ? (
          <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-neutral-200">
            <div className="text-neutral-900 dark:text-neutral-100">
              <span className="font-semibold">Template:</span> {uploaded.filename} ({uploaded.kind})
            </div>
            <div className="mt-1 text-neutral-700 dark:text-neutral-300">{uploaded.summary}</div>
          </div>
        ) : null}

        {error ? <div className="mt-2 text-xs text-rose-400">{error}</div> : null}
      </motion.button>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) void handleFile(file)
          e.currentTarget.value = ''
        }}
      />
    </div>
  )
}
