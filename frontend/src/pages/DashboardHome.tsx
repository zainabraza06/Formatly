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

 const save = async (id: string, title: string, kind: 'docx' | 'pdf') => {
 setSaving(`${id}:${kind}`)
 setError(null)
 try {
 await (kind === 'docx' ? api.exportDocx(id, title) : api.exportPdf(id, title))
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
 <div className="space-y-8">
 {/* ── Page header ── */}
 <div>
 <motion.h1 
 initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
 className="text-3xl font-bold tracking-tight text-ink"
 >
 Home
 </motion.h1>
 <motion.p 
 initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }}
 className="mt-2 text-base text-muted max-w-2xl"
 >
 AI-powered document production — prompt to polished export in seconds.
 </motion.p>
 </div>

 {/* ── Quick actions ── */}
 <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
 {quickActions.map((a, i) => (
 <motion.div
 key={a.to}
 initial={{ opacity: 0, y: 15 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ duration: 0.3, delay: i * 0.1 }}
 whileHover={{ y: -2 }}
 >
 <Link
 to={a.to}
 className={`flex items-center gap-4 rounded-2xl border ${a.border} ${a.color} p-5 shadow-sm transition-all hover:shadow-md active:scale-[0.98]`}
 >
 <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-2 ${a.textColor} shadow-sm border border-line`}>
 {a.icon}
 </div>
 <div>
 <div className={`text-base font-bold ${a.textColor}`}>{a.label}</div>
 <div className="text-xs font-medium text-muted mt-0.5">{a.desc}</div>
 </div>
 </Link>
 </motion.div>
 ))}
 </div>

 {/* ── Recent + Demo flow ── */}
 <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
 {/* Recent documents */}
 <GlassCard className="xl:col-span-2">
 <div className="flex items-center justify-between mb-4">
 <div className="text-lg font-bold text-ink">Recent documents</div>
 <Link to="/app/files" className="text-sm font-semibold text-focus hover:underline">
 View all →
 </Link>
 </div>

 <div className="space-y-3">
 {recent.length ? (
 recent.map((d, i) => (
 <motion.div
 key={d.document_id}
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ duration: 0.3, delay: i * 0.05 }}
 className="flex items-center justify-between rounded-xl border border-line bg-surface px-4 py-3 shadow-sm hover:shadow-md transition-shadow"
 >
 <div>
 <div className="text-sm font-bold text-ink">{d.title}</div>
 <div className="mt-1 flex items-center gap-2">
 <span className="rounded-md bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-muted border border-line">
 {d.style_preset}
 </span>
 </div>
 </div>
 <div className="flex gap-2">
 <button
 onClick={() => save(d.document_id, d.title, 'docx')}
 disabled={saving !== null}
 className="rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-bold text-ink transition hover:bg-surface-2 hover:border-line-strong shadow-sm disabled:opacity-50"
 >
 {saving === `${d.document_id}:docx` ? '…' : 'DOCX'}
 </button>
 <button
 onClick={() => save(d.document_id, d.title, 'pdf')}
 disabled={saving !== null}
 className="rounded-lg border border-line bg-surface-2 px-3 py-1.5 text-xs font-bold text-ink transition hover:bg-surface hover:border-line-strong shadow-sm disabled:opacity-50"
 >
 {saving === `${d.document_id}:pdf` ? '…' : 'PDF'}
 </button>
 </div>
 </motion.div>
 ))
 ) : (
 <div className="rounded-2xl border-2 border-dashed border-line p-8 text-center bg-surface-2/50">
 <div className="text-sm text-muted font-medium">
 No documents yet.{' '}
 <Link to="/app/compose" className="font-bold text-focus hover:underline">
 Generate your first →
 </Link>
 </div>
 </div>
 )}
 {error && <div className="mt-2 text-xs font-medium text-danger bg-danger/10 p-2 rounded-lg">{error}</div>}
 </div>
 </GlassCard>

 {/* Demo flow */}
 <GlassCard>
 <div className="text-lg font-bold text-ink">Quick start</div>
 <div className="mt-1.5 text-sm text-muted">From material to a finished document in four steps.</div>

 <ol className="mt-6 space-y-4">
 {demoSteps.map((step, i) => (
 <li key={i} className="flex items-start gap-3">
 <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-bold text-ink border border-line shadow-sm">
 {i + 1}
 </span>
 <span className="text-sm leading-relaxed text-muted font-medium">{step}</span>
 </li>
 ))}
 </ol>

 <div className="mt-8">
 <Link
 to="/app/compose"
 className="inline-flex w-full items-center justify-center rounded-xl bg-focus px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-focus/20 transition hover:-translate-y-0.5 hover:shadow-lg hover:shadow-focus/30 active:translate-y-0"
 >
 Create a Document
 </Link>
 </div>
 </GlassCard>
 </div>
 </div>
 )
}
