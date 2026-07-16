import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ThemeToggle } from '../components/ThemeToggle'
import { getInitialTheme, applyTheme } from '../lib/theme'
import { useState, useEffect } from 'react'

const features = [
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
      </svg>
    ),
    title: 'Template Cloning',
    desc: 'Upload a DOCX or PDF and the AI mirrors its exact structure, fonts, and layout to generate new content.',
    accent: 'from-violet-500/20 to-purple-500/10',
    border: 'border-violet-500/20',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
    ),
    title: 'Formatting Automation',
    desc: 'Describe fonts, margins, spacing in plain English. The engine parses and applies rules to every section.',
    accent: 'from-sky-500/20 to-blue-500/10',
    border: 'border-sky-500/20',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
    ),
    title: 'Embedded Charts',
    desc: 'Generate bar, line, and pie charts from manual data or AI suggestions — embedded directly in exports.',
    accent: 'from-emerald-500/20 to-teal-500/10',
    border: 'border-emerald-500/20',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
    ),
    title: 'One-Click Export',
    desc: 'Download polished DOCX and PDF outputs with all formatting, charts, and structure fully preserved.',
    accent: 'from-orange-500/20 to-amber-500/10',
    border: 'border-orange-500/20',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
      </svg>
    ),
    title: 'Style Presets',
    desc: 'Academic, Business, Research, Technical, Resume, Presentation — each preset wires the right typography and layout.',
    accent: 'from-rose-500/20 to-pink-500/10',
    border: 'border-rose-500/20',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
      </svg>
    ),
    title: 'AI Chat Assistant',
    desc: 'Refine sections, change tone, or regenerate content with an integrated AI assistant.',
    accent: 'from-cyan-500/20 to-indigo-500/10',
    border: 'border-cyan-500/20',
  },
]

const pipeline = [
  { label: 'User Prompt', desc: 'Natural language input', color: 'bg-violet-500' },
  { label: 'Intent Extraction', desc: 'AI reads requirements', color: 'bg-purple-500' },
  { label: 'Document Planning', desc: 'Outline & structure built', color: 'bg-blue-500' },
  { label: 'Content Generation', desc: 'Sections written by AI', color: 'bg-sky-500' },
  { label: 'Formatting Engine', desc: 'Rules applied precisely', color: 'bg-emerald-500' },
  { label: 'Export Engine', desc: 'DOCX & PDF rendered', color: 'bg-orange-500' },
]

const testimonials = [
  {
    quote: 'Formatly turned our research prompt into a client-ready report in minutes. Incredible.',
    author: 'Dr. A. Rahman',
    role: 'Research Lead',
  },
  {
    quote: 'Template cloning made our CV generation instantly consistent across 200+ applicants.',
    author: 'Sarah K.',
    role: 'Talent Ops Manager',
  },
  {
    quote: 'The formatting engine actually respects my university style guide. Finally.',
    author: 'Marcus T.',
    role: 'Graduate Student',
  },
]

export function LandingPage() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => getInitialTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-neutral-100 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950 selection:bg-violet-500/20">

      {/* ── Ambient glow ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/4 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-violet-500/10 blur-[120px] dark:bg-violet-500/8" />
        <div className="absolute -bottom-20 right-1/4 h-[400px] w-[400px] translate-x-1/2 rounded-full bg-sky-500/10 blur-[100px] dark:bg-sky-500/8" />
      </div>

      <div className="relative mx-auto max-w-6xl px-4 pb-20">

        {/* ── Nav ── */}
        <header className="flex items-center justify-between py-5">
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="flex items-center gap-2"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-purple-600 shadow-lg shadow-violet-500/25">
              <span className="text-sm font-bold text-white">F</span>
            </div>
            <span className="text-sm font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
              Formatly
            </span>
          </motion.div>

          <div className="flex items-center gap-3">
            <ThemeToggle mode={theme} onToggle={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} />
            <Link
              to="/app/compose"
              className="rounded-xl bg-neutral-900 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-neutral-700 dark:bg-white dark:text-neutral-950 dark:hover:bg-neutral-200"
            >
              Open App →
            </Link>
          </div>
        </header>

        {/* ── Hero ── */}
        <section className="mt-16 text-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-medium text-violet-600 dark:text-violet-400">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-500 animate-pulse" />
              AI Document Agent
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
            className="mt-5 text-5xl font-bold tracking-tight text-neutral-900 dark:text-neutral-50 sm:text-6xl"
          >
            Generate{' '}
            <span className="bg-gradient-to-r from-violet-600 via-purple-600 to-sky-500 bg-clip-text text-transparent">
              Professional
            </span>
            <br />
            Documents with AI
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="mt-5 mx-auto max-w-xl text-base leading-7 text-neutral-600 dark:text-neutral-400"
          >
            From prompts to fully formatted reports, resumes, and proposals in seconds.
            Formatly acts like an autonomous document-production platform.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            className="mt-7 flex flex-wrap items-center justify-center gap-3"
          >
            <Link
              to="/app/compose"
              className="rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/30 transition hover:shadow-violet-500/50 hover:scale-[1.02] active:scale-[0.98]"
            >
              Start a New Document
            </Link>
            <Link
              to="/app/templates"
              className="rounded-xl border border-neutral-200/80 bg-white/60 px-6 py-2.5 text-sm font-semibold text-neutral-800 backdrop-blur-sm transition hover:bg-white/80 dark:border-white/10 dark:bg-white/5 dark:text-neutral-200 dark:hover:bg-white/10"
            >
              Upload a Template
            </Link>
          </motion.div>
        </section>

        {/* ── Feature grid ── */}
        <section className="mt-24">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="mb-10 text-center"
          >
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Everything you need</h2>
            <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
              A complete document-production pipeline in one tool.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: i * 0.05 }}
                whileHover={{ y: -3 }}
                className={`group rounded-2xl border ${f.border} bg-gradient-to-br ${f.accent} p-5 backdrop-blur-sm transition-shadow hover:shadow-lg dark:border-opacity-30`}
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/60 text-neutral-700 shadow-sm ring-1 ring-neutral-200/60 dark:bg-white/10 dark:text-neutral-300 dark:ring-white/10">
                  {f.icon}
                </div>
                <div className="mt-4 text-sm font-semibold text-neutral-900 dark:text-neutral-100">{f.title}</div>
                <div className="mt-1.5 text-xs leading-5 text-neutral-600 dark:text-neutral-400">{f.desc}</div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Pipeline + Demo ── */}
        <section className="mt-24 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Pipeline visualization */}
          <motion.div
            initial={{ opacity: 0, x: -16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className="rounded-2xl border border-white/10 bg-white/40 p-6 backdrop-blur-md dark:bg-white/5"
          >
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">AI Document Pipeline</div>
            <div className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
              Each request passes through a multi-stage agent.
            </div>
            <div className="mt-5 space-y-2.5">
              {pipeline.map((step, i) => (
                <motion.div
                  key={step.label}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.28, delay: i * 0.06 }}
                  className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/30 px-4 py-2.5 dark:bg-white/5"
                >
                  <div className={`h-2 w-2 shrink-0 rounded-full ${step.color}`} />
                  <div className="flex-1">
                    <div className="text-xs font-medium text-neutral-900 dark:text-neutral-100">{step.label}</div>
                    <div className="text-[11px] text-neutral-500 dark:text-neutral-400">{step.desc}</div>
                  </div>
                  <div className="text-[10px] font-medium text-neutral-400 dark:text-neutral-500">
                    {i === 3 ? '✦ AI' : '✓'}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Demo flow */}
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className="flex flex-col gap-4"
          >
            {/* Demo 1 */}
            <div className="rounded-2xl border border-white/10 bg-white/40 p-5 backdrop-blur-md dark:bg-white/5">
              <div className="flex items-center gap-2">
                <span className="rounded-lg bg-violet-500/15 px-2 py-0.5 text-[11px] font-semibold text-violet-600 dark:text-violet-400">
                  Demo A
                </span>
                <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">CV from Template</div>
              </div>
              <ol className="mt-3 space-y-2 text-xs text-neutral-600 dark:text-neutral-400">
                {['Upload a CV template (DOCX)', 'Paste personal information', 'AI generates matching CV', 'Export PDF'].map((step, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-[10px] font-bold text-violet-600 dark:text-violet-400">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
              <Link
                to="/app/templates"
                className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-violet-600 hover:text-violet-500 dark:text-violet-400"
              >
                Try it → Templates
              </Link>
            </div>

            {/* Demo 2 */}
            <div className="rounded-2xl border border-white/10 bg-white/40 p-5 backdrop-blur-md dark:bg-white/5">
              <div className="flex items-center gap-2">
                <span className="rounded-lg bg-sky-500/15 px-2 py-0.5 text-[11px] font-semibold text-sky-600 dark:text-sky-400">
                  Demo B
                </span>
                <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Academic Report</div>
              </div>
              <ol className="mt-3 space-y-2 text-xs text-neutral-600 dark:text-neutral-400">
                {['Enter topic + formatting rules', 'AI plans & structures report', 'Sections + charts generated', 'Export DOCX or PDF'].map((step, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-500/15 text-[10px] font-bold text-sky-600 dark:text-sky-400">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
              <Link
                to="/app/compose"
                className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-sky-600 hover:text-sky-500 dark:text-sky-400"
              >
                Try it → New Document
              </Link>
            </div>
          </motion.div>
        </section>

        {/* ── Testimonials ── */}
        <section className="mt-24">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
            className="mb-8 text-center"
          >
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">What people say</h2>
          </motion.div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {testimonials.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: i * 0.07 }}
                className="rounded-2xl border border-white/10 bg-white/40 p-5 backdrop-blur-md dark:bg-white/5"
              >
                <svg className="h-5 w-5 text-violet-500/60" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" />
                </svg>
                <p className="mt-3 text-xs leading-5 text-neutral-700 dark:text-neutral-300">"{t.quote}"</p>
                <div className="mt-4">
                  <div className="text-xs font-semibold text-neutral-900 dark:text-neutral-100">{t.author}</div>
                  <div className="text-[11px] text-neutral-500 dark:text-neutral-400">{t.role}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Bottom CTA ── */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
          className="mt-24 rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 via-purple-500/5 to-sky-500/10 p-10 text-center backdrop-blur-sm"
        >
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            Ready to generate your first document?
          </h2>
          <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
            No configuration needed — just describe what you want.
          </p>
          <Link
            to="/app/compose"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-500/30 transition hover:shadow-violet-500/50 hover:scale-[1.02] active:scale-[0.98]"
          >
            Open Formatly App →
          </Link>
        </motion.section>

        {/* ── Footer ── */}
        <footer className="mt-14 flex flex-wrap items-center justify-between gap-2 border-t border-neutral-200/60 pt-6 text-xs text-neutral-500 dark:border-white/10 dark:text-neutral-500">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-purple-600">
              <span className="text-[9px] font-bold text-white">F</span>
            </div>
            <span>© {new Date().getFullYear()} Formatly</span>
          </div>
          <div>AI-powered document production platform</div>
        </footer>

      </div>
    </div>
  )
}
