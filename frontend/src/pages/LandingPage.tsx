import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GlassCard } from '../components/GlassCard'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-200 dark:from-neutral-950 dark:to-neutral-900">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <header className="flex items-center justify-between">
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">DocPilot AI</div>
          <div className="flex items-center gap-2">
            <Link
              to="/app/new"
              className="rounded-xl bg-neutral-900 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-neutral-800 dark:bg-white dark:text-neutral-950"
            >
              Open App
            </Link>
          </div>
        </header>

        <section className="mt-12 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div>
            <motion.h1
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
              className="text-4xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-5xl"
            >
              Generate Professional Documents with AI
            </motion.h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-neutral-700 dark:text-neutral-300">
              From prompts to fully formatted reports, resumes, and proposals in seconds.
              DocPilot AI acts like an autonomous document-generation agent.
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              <Link
                to="/app/new"
                className="rounded-xl bg-neutral-900 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-neutral-800 dark:bg-white dark:text-neutral-950"
              >
                Start a New Document
              </Link>
              <Link
                to="/app/templates"
                className="rounded-xl border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold text-neutral-900 backdrop-blur-md transition hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
              >
                Upload a Template
              </Link>
            </div>

            <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {[
                {
                  title: 'Template Cloning',
                  desc: 'Upload a DOCX and generate new content in the same structure & style.',
                },
                {
                  title: 'Formatting Automation',
                  desc: 'Extract rules (font, spacing, margins) and apply consistently.',
                },
                {
                  title: 'Charts in Docs',
                  desc: 'Generate bar/line/pie charts and embed them into exports.',
                },
                {
                  title: 'Export Engine',
                  desc: 'Download polished DOCX and PDF outputs.',
                },
              ].map((f) => (
                <GlassCard key={f.title} className="p-4">
                  <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                    {f.title}
                  </div>
                  <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">{f.desc}</div>
                </GlassCard>
              ))}
            </div>
          </div>

          <GlassCard className="p-6">
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">AI Document Pipeline</div>
            <div className="mt-3 grid gap-2">
              {[
                'User Prompt',
                'Intent Extraction',
                'Document Planning',
                'Content Generation',
                'Formatting Engine',
                'Export Engine',
              ].map((s, i) => (
                <motion.div
                  key={s}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.05 }}
                  className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2"
                >
                  <div className="text-xs font-medium text-neutral-900 dark:text-neutral-100">{s}</div>
                  <div className="text-[11px] text-neutral-700 dark:text-neutral-300">{i === 3 ? 'AI thinks…' : 'Ready'}</div>
                </motion.div>
              ))}
            </div>

            <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs font-semibold text-neutral-900 dark:text-neutral-100">Testimonials</div>
              <div className="mt-2 text-xs text-neutral-700 dark:text-neutral-300">
                “DocPilot AI turned our prompt into a client-ready report in minutes.”
              </div>
              <div className="mt-2 text-xs text-neutral-700 dark:text-neutral-300">
                “Template cloning made our CV generation instantly consistent.”
              </div>
            </div>
          </GlassCard>
        </section>

        <footer className="mt-12 flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-400">
          <div>© {new Date().getFullYear()} DocPilot AI</div>
          <div className="opacity-80">Hackathon-ready, production feel</div>
        </footer>
      </div>
    </div>
  )
}
