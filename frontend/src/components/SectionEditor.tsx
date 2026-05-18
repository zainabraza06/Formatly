import { motion } from 'framer-motion'
import type { DocumentSection, Tone } from '../types/api'

export function SectionEditor({
  section,
  onChange,
  onRewrite,
  busyTone,
}: {
  section: DocumentSection
  onChange: (next: DocumentSection) => void
  onRewrite: (tone: Tone) => void
  busyTone?: Tone | null
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          {section.heading}
        </div>
        <div className="flex items-center gap-2">
          {(['formal', 'simple', 'technical'] as Tone[]).map((t) => (
            <motion.button
              key={t}
              type="button"
              whileTap={{ scale: 0.98 }}
              onClick={() => onRewrite(t)}
              disabled={busyTone === t}
              className="rounded-xl border border-white/10 bg-white/10 px-3 py-1 text-xs text-neutral-800 transition hover:bg-white/15 disabled:opacity-60 dark:text-neutral-100"
            >
              {busyTone === t ? 'Rewriting…' : `Rewrite: ${t}`}
            </motion.button>
          ))}
        </div>
      </div>

      <textarea
        value={section.content}
        onChange={(e) => onChange({ ...section, content: e.target.value })}
        className="mt-3 h-36 w-full resize-none rounded-xl border border-white/10 bg-transparent p-3 text-sm text-neutral-900 outline-none placeholder:text-neutral-500 focus:ring-2 focus:ring-sky-400/30 dark:text-neutral-100"
        placeholder="AI output will appear here. You can edit freely."
      />
    </div>
  )
}
