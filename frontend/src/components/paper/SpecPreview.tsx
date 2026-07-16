import { useState } from 'react'
import { GlassCard } from '../GlassCard'
import type { PaperSpec } from '../../lib/paperApi'

/** Shows what the AI decided: outline, tables, and the explicit visualisation plan. */
export function SpecPreview({ spec }: { spec: PaperSpec }) {
  const [showJson, setShowJson] = useState(false)

  const headings = spec.blocks.filter((b) => b.type === 'heading')
  const tables = spec.blocks.filter((b) => b.type === 'table')
  const figures = spec.blocks.filter((b) => b.type === 'figure')

  return (
    <GlassCard className="space-y-3">
      <div>
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          {spec.meta.title}
        </div>
        <div className="mt-1 flex flex-wrap gap-1">
          {spec.meta.keywords.map((k) => (
            <span key={k} className="rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] text-violet-600 dark:text-violet-300">
              {k}
            </span>
          ))}
        </div>
      </div>

      <Stat items={[
        ['Sections', String(headings.length)],
        ['Tables', String(tables.length)],
        ['Figures', String(figures.length)],
        ['Refs', String(spec.references.length)],
      ]} />

      {spec.meta.abstract && (
        <Section title="Abstract">
          <p className="line-clamp-4 text-[11px] leading-relaxed text-neutral-600 dark:text-neutral-300">
            {spec.meta.abstract}
          </p>
        </Section>
      )}

      <Section title="Outline">
        <ul className="space-y-0.5">
          {headings.slice(0, 12).map((h, i) => (
            <li key={i} className="text-[11px] text-neutral-600 dark:text-neutral-300"
                style={{ paddingLeft: `${((h.level as number) - 1) * 10}px` }}>
              {h.text as string}
            </li>
          ))}
        </ul>
      </Section>

      {spec.visualization_plan.length > 0 && (
        <Section title={`Visualisation plan (${spec.visualization_plan.length})`}>
          <ul className="space-y-1.5">
            {spec.visualization_plan.map((v, i) => (
              <li key={i} className="rounded-lg border border-white/10 bg-white/5 p-2">
                <div className="flex items-center gap-1.5">
                  <span className="rounded bg-sky-500/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-sky-600 dark:text-sky-300">
                    {v.kind}
                  </span>
                  <span className="truncate text-[11px] text-neutral-700 dark:text-neutral-200">{v.data}</span>
                </div>
                <div className="mt-0.5 text-[10px] italic text-neutral-500">{v.rationale}</div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <button
        onClick={() => setShowJson((s) => !s)}
        className="w-full rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-[11px] font-medium text-neutral-600 hover:bg-white/10 dark:text-neutral-300"
      >
        {showJson ? 'Hide' : 'View'} formatted JSON
      </button>
      {showJson && (
        <pre className="max-h-72 overflow-auto rounded-lg bg-neutral-900 p-3 text-[9px] leading-relaxed text-neutral-200">
          {JSON.stringify(spec, null, 2)}
        </pre>
      )}
    </GlassCard>
  )
}

function Stat({ items }: { items: [string, string][] }) {
  return (
    <div className="grid grid-cols-4 gap-1">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-lg bg-white/5 py-1.5 text-center">
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{value}</div>
          <div className="text-[9px] uppercase tracking-wide text-neutral-500">{label}</div>
        </div>
      ))}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">{title}</div>
      {children}
    </div>
  )
}
