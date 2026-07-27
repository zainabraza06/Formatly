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
    <div className="rounded-2xl border border-line bg-surface-2 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-ink">
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
              className="rounded-xl border border-line bg-surface px-3 py-1 text-xs text-ink transition hover:bg-surface-2 disabled:opacity-60 "
            >
              {busyTone === t ? 'Rewriting…' : `Rewrite: ${t}`}
            </motion.button>
          ))}
        </div>
      </div>

      <textarea
        value={section.content}
        onChange={(e) => onChange({ ...section, content: e.target.value })}
        className="mt-3 h-36 w-full resize-none rounded-xl border border-line bg-transparent p-3 text-sm text-ink outline-none placeholder:text-muted focus:ring-2 focus:ring-sky-400/30 "
        placeholder="AI output will appear here. You can edit freely."
      />
    </div>
  )
}
