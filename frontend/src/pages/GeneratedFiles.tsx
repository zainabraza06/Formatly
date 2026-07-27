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
 <div className="text-sm font-semibold text-ink">Generated files</div>
 <div className="mt-1 text-xs text-muted">
 Download exports for your recent drafts.
 </div>

 <div className="mt-4 space-y-2">
 {recent.map((d) => (
 <div
 key={d.document_id}
 className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface-2 px-3 py-2"
 >
 <div>
 <div className="text-xs font-semibold text-ink">{d.title}</div>
 <div className="text-[11px] text-muted">Preset: {d.style_preset}</div>
 </div>
 <div className="flex gap-2">
 <a
 className="rounded-xl border border-line bg-surface px-3 py-1 text-[11px] text-ink hover:bg-surface-2 "
 href={api.exportDocxUrl(d.document_id)}
 >
 Download DOCX
 </a>
 <a
 className="rounded-xl bg-accent px-3 py-1 text-[11px] text-accent-fg "
 href={api.exportPdfUrl(d.document_id)}
 >
 Download PDF
 </a>
 </div>
 </div>
 ))}

 {!recent.length ? (
 <div className="text-xs text-muted">No exports yet.</div>
 ) : null}

 {error ? <div className="text-xs text-rose-400">{error}</div> : null}
 </div>
 </GlassCard>
 )
}
