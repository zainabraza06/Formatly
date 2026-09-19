import { Button } from '../ui'
import { CheckIcon, SparkIcon, UndoIcon } from '../icons'
import type { ReviewState } from '../../hooks/useDocOS'

/**
 * The bar that appears after the assistant has changed something.
 *
 * The edit is already in the document — the engine commits it — so this is not
 * a pending change to approve. It is the moment where the change is named, can
 * be looked at in detail, and can be taken back in one click, before it
 * disappears into the version history like every other edit.
 */
export function ChangeReview({
  review,
  busy,
  onKeep,
  onUndo,
  onShowChanges,
}: {
  review: ReviewState
  busy?: boolean
  onKeep: () => void
  onUndo: () => void
  onShowChanges: () => void
}) {
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-brand/25 bg-brand-soft px-3 py-2.5 shadow-sm animate-fade-up"
    >
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-brand text-brand-fg" aria-hidden>
        <SparkIcon className="h-3.5 w-3.5" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">
          {review.summary || 'The assistant edited the document'}
        </p>
        <p className="truncate text-2xs text-muted">
          From “{review.command}” · version {review.before} → {review.after}
        </p>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onShowChanges} disabled={busy}>
          See what changed
        </Button>
        <Button variant="secondary" size="sm" onClick={onUndo} disabled={busy} leadingIcon={<UndoIcon />}>
          Undo
        </Button>
        <Button variant="primary" size="sm" onClick={onKeep} disabled={busy} leadingIcon={<CheckIcon />}>
          Keep
        </Button>
      </div>
    </div>
  )
}
