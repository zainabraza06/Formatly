import type { DocumentSection } from '../types/api'

export function PreviewPanel({
  title,
  sections,
}: {
  title: string
  sections: DocumentSection[]
}) {
  return (
    <div className="h-full overflow-auto rounded-2xl border border-line bg-surface-2 p-5">
      <div className="text-lg font-semibold text-ink">{title}</div>
      <div className="mt-4 space-y-4">
        {sections.map((s) => (
          <div key={s.id}>
            <div className="text-sm font-semibold text-ink">
              {s.heading}
            </div>
            <div className="mt-1 whitespace-pre-wrap text-sm text-muted">
              {s.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
