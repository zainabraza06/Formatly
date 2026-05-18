import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GlassCard } from '../components/GlassCard'
import { api } from '../lib/api'
import type { RecentDocument } from '../types/api'

const quickActions = [
  {
    to: '/app/new',
    label: 'New Document',
    desc: 'Prompt → formatted doc',
    color: 'from-violet-500/15 to-purple-500/10',
    border: 'border-violet-500/20',
    textColor: 'text-violet-700 dark:text-violet-300',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
        <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
      </svg>
    ),
  },
  {
    to: '/app/templates',
    label: 'Templates',
    desc: 'Clone a document style',
    color: 'from-sky-500/15 to-blue-500/10',
    border: 'border-sky-500/20',
    textColor: 'text-sky-700 dark:text-sky-300',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    to: '/app/assistant',
    label: 'AI Assistant',
    desc: 'Refine & rewrite',
    color: 'from-emerald-500/15 to-teal-500/10',
    border: 'border-emerald-500/20',
    textColor: 'text-emerald-700 dark:text-emerald-300',
    icon: (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
        <path d="M3.505 2.365A41.369 41.369 0 019 2c1.863 0 3.697.124 5.495.365 1.247.167 2.18 1.108 2.435 2.268a4.45 4.45 0 00-.577-.069 43.141 43.141 0 00-4.706 0C9.229 4.696 7.5 6.727 7.5 8.998v2.24c0 1.413.67 2.735 1.76 3.562l-2.98 2.98A.75.75 0 015 17.25v-3.443c-.501-.048-1-.106-1.495-.172C2.033 13.438 1 12.162 1 10.72V5.28c0-1.441 1.033-2.717 2.505-2.914z" />
        <path d="M14 6c-.762 0-1.52.02-2.271.062C10.157 6.148 9 7.472 9 8.998v2.24c0 1.519 1.147 2.839 2.71 2.935.214.013.428.024.642.034.2.009.385.09.518.224l2.35 2.35a.75.75 0 001.28-.531v-2.07c1.453-.195 2.5-1.463 2.5-2.915V8.998c0-1.526-1.157-2.85-2.729-2.936A41.645 41.645 0 0014 6z" />
      </svg>
    ),
  },
]

const demoSteps = [
  'Upload a CV template (DOCX)',
  'Paste personal info',
  'AI generates matching CV',
  'Export PDF',
]

export function DashboardHome() {
  const [recent, setRecent] = useState<RecentDocument[]>([])
  const [error, setError] = useState<string | null>(null)

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

      {/* ── Welcome banner ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-500/10 via-purple-500/8 to-sky-500/10 p-5"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-purple-600 shadow-lg shadow-violet-500/30">
            <span className="text-base font-bold text-white">F</span>
          </div>
          <div>
            <div className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Welcome to Formatly</div>
            <div className="mt-0.5 text-xs text-neutral-600 dark:text-neutral-400">
              AI-powered document production — prompt to polished export in seconds.
            </div>
          </div>
        </div>
      </motion.div>

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
              className={`flex items-center gap-3 rounded-2xl border ${a.border} bg-gradient-to-br ${a.color} p-4 transition-all hover:shadow-md hover:scale-[1.01]`}
            >
              <div className={`shrink-0 ${a.textColor}`}>{a.icon}</div>
              <div>
                <div className={`text-sm font-semibold ${a.textColor}`}>{a.label}</div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">{a.desc}</div>
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
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Recent documents</div>
            <Link to="/app/files" className="text-xs text-violet-600 hover:text-violet-500 dark:text-violet-400">
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
                  className="flex items-center justify-between rounded-xl border border-white/10 bg-white/30 px-3 py-2.5 dark:bg-white/5"
                >
                  <div>
                    <div className="text-xs font-semibold text-neutral-900 dark:text-neutral-100">{d.title}</div>
                    <div className="mt-0.5 flex items-center gap-1.5">
                      <span className="rounded-md bg-neutral-100/80 px-1.5 py-0.5 text-[10px] font-medium text-neutral-600 dark:bg-white/10 dark:text-neutral-400">
                        {d.style_preset}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <a
                      href={api.exportDocxUrl(d.document_id)}
                      className="rounded-lg border border-white/10 bg-white/30 px-2.5 py-1 text-[11px] font-medium text-neutral-700 transition hover:bg-white/50 dark:bg-white/8 dark:text-neutral-300"
                    >
                      DOCX
                    </a>
                    <a
                      href={api.exportPdfUrl(d.document_id)}
                      className="rounded-lg border border-violet-500/20 bg-violet-500/10 px-2.5 py-1 text-[11px] font-medium text-violet-700 transition hover:bg-violet-500/20 dark:text-violet-300"
                    >
                      PDF
                    </a>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="rounded-xl border border-dashed border-neutral-300/60 p-6 text-center dark:border-white/10">
                <div className="text-xs text-neutral-500 dark:text-neutral-400">
                  No documents yet.{' '}
                  <Link to="/app/new" className="font-semibold text-violet-600 hover:underline dark:text-violet-400">
                    Generate your first →
                  </Link>
                </div>
              </div>
            )}
            {error && <div className="text-xs text-rose-500">{error}</div>}
          </div>
        </GlassCard>

        {/* Demo flow */}
        <GlassCard>
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Quick demo flow</div>
          <div className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Try template cloning in 4 steps.</div>

          <ol className="mt-4 space-y-3">
            {demoSteps.map((step, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-[10px] font-bold text-violet-600 dark:text-violet-400">
                  {i + 1}
                </span>
                <span className="text-xs leading-5 text-neutral-700 dark:text-neutral-300">{step}</span>
              </li>
            ))}
          </ol>

          <div className="mt-5 grid grid-cols-2 gap-2">
            <Link
              to="/app/templates"
              className="rounded-xl border border-neutral-200/60 bg-white/50 px-3 py-2 text-center text-xs font-semibold text-neutral-700 transition hover:bg-white/70 dark:border-white/10 dark:bg-white/5 dark:text-neutral-300"
            >
              Templates
            </Link>
            <Link
              to="/app/new"
              className="rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-3 py-2 text-center text-xs font-semibold text-white shadow-sm shadow-violet-500/25 transition hover:shadow-violet-500/40"
            >
              New Doc
            </Link>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
