import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GlassCard } from '../components/GlassCard'
import { api } from '../lib/api'
import type { RecentDocument } from '../types/api'

const quickActions = [
 {
 to: '/app/compose',
 label: 'New Document',
 desc: 'Prompt → formatted doc',
 color: 'bg-surface-2',
 border: 'border-line',
 textColor: 'text-ink',
 icon: (
 <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
 <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
 </svg>
 ),
 },
 {
 to: '/app/editor',
 label: 'AI Assistant',
 desc: 'Refine & rewrite',
 color: 'bg-surface',
 border: 'border-line',
 textColor: 'text-ink',
 icon: (
 <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
 <path d="M3.505 2.365A41.369 41.369 0 019 2c1.863 0 3.697.124 5.495.365 1.247.167 2.18 1.108 2.435 2.268a4.45 4.45 0 00-.577-.069 43.141 43.141 0 00-4.706 0C9.229 4.696 7.5 6.727 7.5 8.998v2.24c0 1.413.67 2.735 1.76 3.562l-2.98 2.98A.75.75 0 015 17.25v-3.443c-.501-.048-1-.106-1.495-.172C2.033 13.438 1 12.162 1 10.72V5.28c0-1.441 1.033-2.717 2.505-2.914z" />
 <path d="M14 6c-.762 0-1.52.02-2.271.062C10.157 6.148 9 7.472 9 8.998v2.24c0 1.519 1.147 2.839 2.71 2.935.214.013.428.024.642.034.2.009.385.09.518.224l2.35 2.35a.75.75 0 001.28-.531v-2.07c1.453-.195 2.5-1.463 2.5-2.915V8.998c0-1.526-1.157-2.85-2.729-2.936A41.645 41.645 0 0014 6z" />
 </svg>
 ),
 },
]

const demoSteps = [
 'Paste your material — notes, data, or an assignment brief',
 'Pick a style and say anything extra it must do',
 'The AI writes it, with tables, charts and code listings',
 'Download the DOCX, or open it in Document OS to edit',
]

export function DashboardHome() {
 const [recent, setRecent] = useState<RecentDocument[]>([])
 const [error, setError] = useState<string | null>(null)
 // Which row is fetching, so its button can say so and cannot be double-clicked.
 const [saving, setSaving] = useState<string | null>(null)

 const save = async (id: string, kind: 'docx' | 'pdf') => {
 setSaving(`${id}:${kind}`)
 setError(null)
 try {
 await (kind === 'docx' ? api.exportDocx(id) : api.exportPdf(id))
 } catch (e) {
 setError(e instanceof Error ? e.message : 'Download failed')
 } finally {
 setSaving(null)
 }
 }

 useEffect(() => {
 let mounted = true
 api
 .recentDocuments()
 .then((r) => { if (mounted) setRecent(r) })
 .catch((e) => { if (mounted) setError(e instanceof Error ? e.message : 'Failed to load') })
 return () => { mounted = false }
 }, [])

 return (
 <div className="space-y-5">

 {/* ── Page header ── */}
 <div>
 <h1 className="text-xl font-semibold tracking-tight text-ink">Home</h1>
 <p className="mt-0.5 text-sm text-muted">
 AI-powered document production — prompt to polished export in seconds.
 </p>
 </div>

 {/* ── Quick actions ── */}
 <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
 {quickActions.map((a, i) => (
 <motion.div
 key={a.to}
 initial={{ opacity: 0, y: 12 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ duration: 0.28, delay: i * 0.06 }}
 >
 <Link
 to={a.to}
 className={`flex items-center gap-3 rounded-xl border ${a.border} ${a.color} p-4 transition-colors hover:bg-surface-2`}
 >
 <div className={`shrink-0 ${a.textColor}`}>{a.icon}</div>
 <div>
 <div className={`text-sm font-semibold ${a.textColor}`}>{a.label}</div>
 <div className="text-xs text-muted">{a.desc}</div>
 </div>
 </Link>
 </motion.div>
 ))}
 </div>

 {/* ── Recent + Demo flow ── */}
 <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">

 {/* Recent documents */}
 <GlassCard className="xl:col-span-2">
 <div className="flex items-center justify-between">
 <div className="text-sm font-semibold text-ink">Recent documents</div>
 <Link to="/app/files" className="text-xs text-ink hover:text-ink dark:text-muted">
 View all →
 </Link>
 </div>

 <div className="mt-3 space-y-2">
 {recent.length ? (
 recent.map((d, i) => (
 <motion.div
 key={d.document_id}
 initial={{ opacity: 0, x: -8 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ duration: 0.22, delay: i * 0.04 }}
 className="flex items-center justify-between rounded-xl border border-line bg-surface px-3 py-2.5 "
 >
 <div>
 <div className="text-xs font-semibold text-ink">{d.title}</div>
 <div className="mt-0.5 flex items-center gap-1.5">
 <span className="rounded-md bg-surface-2/80 px-1.5 py-0.5 text-[10px] font-medium text-muted ">
 {d.style_preset}
 </span>
 </div>
 </div>
 <div className="flex gap-1.5">
 <button
 onClick={() => save(d.document_id, 'docx')}
 disabled={saving !== null}
 className="rounded-lg border border-line bg-surface px-2.5 py-1 text-[11px] font-medium text-ink transition hover:bg-surface-2 disabled:opacity-50"
 >
 {saving === `${d.document_id}:docx` ? '…' : 'DOCX'}
 </button>
 <button
 onClick={() => save(d.document_id, 'pdf')}
 disabled={saving !== null}
 className="rounded-lg border border-line bg-surface-2 px-2.5 py-1 text-[11px] font-medium text-ink transition hover:bg-surface-2 disabled:opacity-50"
 >
 {saving === `${d.document_id}:pdf` ? '…' : 'PDF'}
 </button>
 </div>
 </motion.div>
 ))
 ) : (
 <div className="rounded-xl border border-dashed border-line/60 p-6 text-center ">
 <div className="text-xs text-muted">
 No documents yet.{' '}
 <Link to="/app/compose" className="font-semibold text-ink hover:underline dark:text-muted">
 Generate your first →
 </Link>
 </div>
 </div>
 )}
 {error && <div className="text-xs text-danger">{error}</div>}
 </div>
 </GlassCard>

 {/* Demo flow */}
 <GlassCard>
 <div className="text-sm font-semibold text-ink">Quick demo flow</div>
 <div className="mt-1 text-xs text-muted">From material to a finished document in four steps.</div>

 <ol className="mt-4 space-y-3">
 {demoSteps.map((step, i) => (
 <li key={i} className="flex items-start gap-2.5">
 <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-2 text-[10px] font-bold text-ink">
 {i + 1}
 </span>
 <span className="text-xs leading-5 text-muted">{step}</span>
 </li>
 ))}
 </ol>

 <div className="mt-5">
 <Link
 to="/app/compose"
 className="rounded-xl bg-accent px-3 py-2 text-center text-xs font-medium text-accent-fg transition hover:opacity-90"
 >
 New Doc
 </Link>
 </div>
 </GlassCard>
 </div>
 </div>
 )
}
