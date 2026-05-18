import type { DocumentSection } from '../types/api'

export function PreviewPanel({
  title,
  sections,
}: {
  title: string
  sections: DocumentSection[]
}) {
  return (
    <div className="h-full overflow-auto rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{title}</div>
      <div className="mt-4 space-y-4">
        {sections.map((s) => (
          <div key={s.id}>
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              {s.heading}
            </div>
            <div className="mt-1 whitespace-pre-wrap text-sm text-neutral-700 dark:text-neutral-300">
              {s.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
