import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { GlassCard } from '../components/GlassCard'
import { api } from '../lib/api'
import type { RecentDocument } from '../types/api'

export function DashboardHome() {
  const [recent, setRecent] = useState<RecentDocument[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    api
      .recentDocuments()
      .then((r) => {
        if (mounted) setRecent(r)
      })
      .catch((e) => {
        if (mounted) setError(e instanceof Error ? e.message : 'Failed to load')
      })
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <GlassCard className="xl:col-span-2">
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Recent documents</div>
        <div className="mt-3 grid gap-2">
          {recent.length ? (
            recent.map((d) => (
              <div
                key={d.document_id}
                className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2"
              >
                <div>
                  <div className="text-xs font-medium text-neutral-900 dark:text-neutral-100">{d.title}</div>
                  <div className="text-[11px] text-neutral-700 dark:text-neutral-300">
                    Preset: {d.style_preset}
                  </div>
                </div>
                <div className="flex gap-2">
                  <a
                    href={api.exportDocxUrl(d.document_id)}
                    className="rounded-lg border border-white/10 bg-white/10 px-3 py-1 text-[11px] text-neutral-900 hover:bg-white/15 dark:text-neutral-100"
                  >
                    DOCX
                  </a>
                  <a
                    href={api.exportPdfUrl(d.document_id)}
                    className="rounded-lg border border-white/10 bg-white/10 px-3 py-1 text-[11px] text-neutral-900 hover:bg-white/15 dark:text-neutral-100"
                  >
                    PDF
                  </a>
                </div>
              </div>
            ))
          ) : (
            <div className="text-xs text-neutral-700 dark:text-neutral-300">
              No documents yet — generate one from <Link to="/app/new" className="underline">New Document</Link>.
            </div>
          )}
          {error ? <div className="text-xs text-rose-400">{error}</div> : null}
        </div>
      </GlassCard>

      <GlassCard>
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Quick demo flow</div>
        <ol className="mt-3 list-decimal space-y-2 pl-4 text-xs text-neutral-700 dark:text-neutral-300">
          <li>Upload a CV template (DOCX)</li>
          <li>Paste personal info</li>
          <li>Generate matching CV</li>
          <li>Export PDF</li>
        </ol>
        <div className="mt-4 flex gap-2">
          <Link
            to="/app/templates"
            className="rounded-xl border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
          >
            Templates
          </Link>
          <Link
            to="/app/new"
            className="rounded-xl bg-neutral-900 px-4 py-2 text-xs font-semibold text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-950"
          >
            New Document
          </Link>
        </div>
      </GlassCard>
    </div>
  )
}
