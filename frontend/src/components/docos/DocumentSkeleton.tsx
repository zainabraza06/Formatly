import { Spinner } from '../ui'

/**
 * The document, before it has arrived.
 *
 * Opening one used to show the same empty state as having none open — the
 * dropzone, reading "Open a Word document" — for as long as the fetch took.
 * On anything but a fast connection that is indistinguishable from a link
 * that does nothing, which is exactly what people reported.
 *
 * So: a page of the right shape, with the title you clicked, and a line
 * saying what is happening. It is a skeleton rather than a spinner alone
 * because the thing being waited for has a known shape, and showing it makes
 * the wait feel like loading rather than like nothing.
 */
export function DocumentSkeleton({ title }: { title?: string | null }) {
  return (
    <div className="flex flex-col items-center gap-4" aria-busy="true">
      <p className="flex items-center gap-2 text-sm text-muted" role="status">
        <Spinner size="sm" />
        {title ? `Opening “${title}”…` : 'Opening the document…'}
      </p>

      {/* A sheet at roughly the proportions of a page, so what arrives lands
          where the eye is already looking. */}
      <div
        className="w-full max-w-[8.5in] rounded-sm bg-white p-[0.9in] shadow-[0_2px_16px_rgba(0,0,0,0.18)] ring-1 ring-black/10"
        aria-hidden
      >
        <Bar className="h-5 w-3/5" />
        <Bar className="mt-3 h-2.5 w-2/5" />

        <div className="mt-10 space-y-3">
          <Bar className="h-2.5 w-full" />
          <Bar className="h-2.5 w-11/12" />
          <Bar className="h-2.5 w-4/5" />
        </div>

        <Bar className="mt-9 h-3.5 w-1/3" />
        <div className="mt-3 space-y-3">
          <Bar className="h-2.5 w-full" />
          <Bar className="h-2.5 w-full" />
          <Bar className="h-2.5 w-3/5" />
        </div>

        <Bar className="mt-9 h-3.5 w-1/4" />
        <div className="mt-3 space-y-3">
          <Bar className="h-2.5 w-full" />
          <Bar className="h-2.5 w-2/3" />
        </div>
      </div>
    </div>
  )
}

/** One line of the page that has not arrived. Slate, not a theme colour: the
 *  sheet is white paper in both themes, so its placeholder is too. */
function Bar({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-full bg-slate-200 ${className}`} />
}
