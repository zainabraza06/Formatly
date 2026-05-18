import { useEffect, useState } from 'react'
import { GlassCard } from '../components/GlassCard'
import { api } from '../lib/api'
import type { RecentDocument } from '../types/api'

export function GeneratedFiles() {
  const [recent, setRecent] = useState<RecentDocument[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .recentDocuments()
      .then(setRecent)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [])

  return (
    <GlassCard>
      <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Generated files</div>
      <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
        Download exports for your recent drafts.
      </div>

      <div className="mt-4 space-y-2">
        {recent.map((d) => (
          <div
            key={d.document_id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2"
          >
            <div>
              <div className="text-xs font-semibold text-neutral-900 dark:text-neutral-100">{d.title}</div>
              <div className="text-[11px] text-neutral-700 dark:text-neutral-300">Preset: {d.style_preset}</div>
            </div>
            <div className="flex gap-2">
              <a
                className="rounded-xl border border-white/10 bg-white/10 px-3 py-1 text-[11px] text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
                href={api.exportDocxUrl(d.document_id)}
              >
                Download DOCX
              </a>
              <a
                className="rounded-xl bg-neutral-900 px-3 py-1 text-[11px] text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-950"
                href={api.exportPdfUrl(d.document_id)}
              >
                Download PDF
              </a>
            </div>
          </div>
        ))}

        {!recent.length ? (
          <div className="text-xs text-neutral-700 dark:text-neutral-300">No exports yet.</div>
        ) : null}

        {error ? <div className="text-xs text-rose-400">{error}</div> : null}
      </div>
    </GlassCard>
  )
}
