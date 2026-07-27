import clsx from 'clsx'
import { motion } from 'framer-motion'
import type { StylePreset } from '../types/api'

const PRESETS: Array<{ id: StylePreset; title: string; desc: string }> = [
  {
    id: 'academic',
    title: 'Academic Paper',
    desc: 'Formal structure, citations placeholders, 1.5 spacing feel.',
  },
  { id: 'business', title: 'Business Report', desc: 'Clear headings, executive summary, concise tone.' },
  { id: 'research', title: 'Research Report', desc: 'Methodical sections, findings, conclusion.' },
  { id: 'technical', title: 'Technical Documentation', desc: 'Implementation-focused, crisp sections.' },
  { id: 'resume', title: 'Resume/CV', desc: 'ATS-friendly sections and compact spacing.' },
  { id: 'presentation', title: 'Presentation Summary', desc: 'Slide-ready bullets and highlights.' },
]

export function StylePresets({
  value,
  onChange,
}: {
  value: StylePreset
  onChange: (v: StylePreset) => void
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {PRESETS.map((p) => {
        const active = p.id === value
        return (
          <motion.button
            key={p.id}
            type="button"
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onChange(p.id)}
            className={clsx(
              'text-left rounded-2xl border p-4 transition',
              'bg-surface  ',
              active
                ? 'border-ink ring-1 ring-focus/40'
                : 'border-line hover:border-line-strong',
            )}
          >
            <div className="text-sm font-semibold text-ink">
              {p.title}
            </div>
            <div className="mt-1 text-xs text-muted">{p.desc}</div>
          </motion.button>
        )
      })}
    </div>
  )
}
