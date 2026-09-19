import { cn } from '../../lib/cn'
import { SparkIcon } from '../icons'

/**
 * The editor, drawn rather than photographed.
 *
 * A screenshot goes stale the first time a button moves, and a stock
 * illustration says nothing about the product. This is the real layout — the
 * document in the middle, the assistant beside it, a change waiting to be kept
 * or undone — built from the same tokens as the app, so it is right in both
 * themes and at every width.
 */
export function ProductMock({ className }: { className?: string }) {
  return (
    <div
      role="img"
      aria-label="The Formatly editor: a Word document in the centre, the AI assistant panel beside it, and a bar offering to keep or undo the change it just made."
      className={cn(
        'overflow-hidden rounded-xl border border-line bg-surface shadow-xl',
        className,
      )}
    >
      {/* Window chrome */}
      <div className="flex items-center gap-2 border-b border-line bg-surface-2/60 px-3 py-2">
        <span className="flex gap-1.5" aria-hidden>
          <Dot /><Dot /><Dot />
        </span>
        <span className="mx-auto rounded-sm border border-line bg-surface px-2 py-0.5 text-2xs text-faint">
          Q3 Churn Report.docx
        </span>
        <span className="hidden items-center gap-1 text-2xs text-success sm:flex" aria-hidden>
          <span className="h-1.5 w-1.5 rounded-full bg-success" /> Live
        </span>
      </div>

      <div className="grid gap-px bg-line sm:grid-cols-[minmax(0,1fr)_38%]">
        {/* The document */}
        <div className="doc-desk p-3 sm:p-4">
          <div className="mx-auto max-w-sm rounded-sm bg-white p-4 shadow-sm">
            <div className="h-2 w-2/3 rounded-full bg-slate-800" />
            <div className="mt-1.5 h-1.5 w-1/3 rounded-full bg-slate-300" />

            <div className="mt-4 space-y-1.5">
              <Line w="w-full" /><Line w="w-11/12" /><Line w="w-4/5" />
            </div>

            {/* The heading the instruction was about */}
            <div className="mt-4 rounded-sm bg-indigo-100 px-1 py-0.5">
              <div className="h-2 w-1/2 rounded-full bg-indigo-500" />
            </div>

            <div className="mt-2 space-y-1.5">
              <Line w="w-full" /><Line w="w-full" /><Line w="w-3/5" />
            </div>

            <div className="mt-4 rounded-sm bg-indigo-100 px-1 py-0.5">
              <div className="h-2 w-2/5 rounded-full bg-indigo-500" />
            </div>
            <div className="mt-2 space-y-1.5">
              <Line w="w-full" /><Line w="w-4/6" />
            </div>
          </div>
        </div>

        {/* The assistant */}
        <div className="flex flex-col gap-2.5 bg-surface p-3">
          <div className="rounded-md border border-line bg-surface-2/60 p-2">
            <p className="text-2xs text-faint">You</p>
            <p className="mt-0.5 text-xs font-medium text-ink">Make all headings consistent</p>
          </div>

          <div className="rounded-md border border-line p-2">
            <p className="flex items-center gap-1.5 text-xs font-medium text-ink">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" aria-hidden />
              Formatted 8 headings
            </p>
            <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-line">
              <div className="h-full w-full rounded-full bg-brand" />
            </div>
            <p className="mt-1.5 text-2xs text-faint">Inter Semibold 14pt · spacing 12pt before</p>
          </div>

          <div className="rounded-md border border-brand/25 bg-brand-soft p-2">
            <p className="flex items-center gap-1.5 text-xs font-medium text-ink">
              <SparkIcon className="h-3.5 w-3.5 text-brand-ink" />
              8 headings changed
            </p>
            <div className="mt-2 flex gap-1.5">
              <span className="rounded-sm bg-brand px-2 py-0.5 text-2xs font-medium text-brand-fg">Keep</span>
              <span className="rounded-sm border border-line bg-surface px-2 py-0.5 text-2xs text-muted">Undo</span>
              <span className="rounded-sm px-2 py-0.5 text-2xs text-muted">See what changed</span>
            </div>
          </div>

          <div className="mt-auto rounded-md border border-line px-2 py-1.5 text-2xs text-faint">
            Tell the assistant what to change…
          </div>
        </div>
      </div>
    </div>
  )
}

function Dot() {
  return <span className="h-2 w-2 rounded-full bg-line-strong" />
}

function Line({ w }: { w: string }) {
  return <div className={cn('h-1.5 rounded-full bg-slate-200', w)} />
}
