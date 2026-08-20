import { useEffect, useRef, useState } from 'react'
import { isAbort, paperApi, type RefinedInstructions } from '../../lib/paperApi'
import { btnGhost, btnPrimary, textarea as uiTextarea } from '../../lib/ui'

/** Refines a loose instruction into one the writer can act on, and keeps
 *  refining until the user is happy: they can accept it, ask for another go, or
 *  say what is wrong and have that fed back in. Nothing is applied until they
 *  press Use — the suggestion never overwrites what they typed behind their back. */
export function InstructionRefiner({
  instructions,
  rawText,
  docKind,
  style,
  onAccept,
  onClose,
}: {
  instructions: string
  rawText: string
  docKind: string
  style: string
  onAccept: (improved: string) => void
  onClose: () => void
}) {
  const [result, setResult] = useState<RefinedInstructions | null>(null)
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [round, setRound] = useState(0)

  const run = async (withFeedback?: string) => {
    setBusy(true)
    setError(null)
    try {
      const res = await paperApi.refineInstructions({
        instructions,
        raw_text: rawText,
        doc_kind: docKind,
        style,
        // Sending the last attempt back with what was wrong makes a retry a
        // correction rather than another roll of the dice.
        previous: result?.improved ?? null,
        feedback: withFeedback ?? null,
      })
      setResult(res)
      setRound((n) => n + 1)
      setFeedback('')
    } catch (e) {
      if (!isAbort(e)) setError(e instanceof Error ? e.message : 'Could not refine')
    } finally {
      setBusy(false)
    }
  }

  // First open: go straight to work rather than making them press again.
  // Guarded by a ref because React runs effects twice in development.
  const started = useRef(false)
  useEffect(() => {
    if (started.current) return
    started.current = true
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="mt-2 rounded-xl border border-line bg-surface-2 p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
          Suggested instructions{round > 1 && ` · attempt ${round}`}
        </span>
        <button
          onClick={onClose}
          className="text-[11px] font-medium text-muted underline-offset-2 hover:text-ink hover:underline"
        >
          Close
        </button>
      </div>

      {busy && (
        <p className="mt-3 text-xs text-muted">
          {round === 0 ? 'Reading your instructions…' : 'Revising…'}
        </p>
      )}

      {error && !busy && (
        <div className="mt-3">
          <p className="text-xs text-danger">{error}</p>
          <button onClick={() => run()} className={`${btnGhost} mt-2`}>
            Try again
          </button>
        </div>
      )}

      {result && !busy && (
        <>
          <pre className="mt-3 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-surface p-3 text-xs leading-relaxed text-ink">
            {result.improved}
          </pre>

          {result.changes.length > 0 && (
            <List label="What changed" items={result.changes} />
          )}
          {result.questions.length > 0 && (
            <List
              label="It needs you to decide"
              items={result.questions}
              hint="Answer in the box below, then ask again."
            />
          )}

          <div className="mt-3 space-y-2">
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={2}
              placeholder="Not quite? Say what to change — e.g. drop the table of contents, add my instructor's name."
              className={uiTextarea}
            />
            <div className="flex flex-wrap gap-2">
              <button onClick={() => onAccept(result.improved)} className={btnPrimary}>
                Use these
              </button>
              <button
                onClick={() => run(feedback.trim() || undefined)}
                disabled={busy}
                className={btnGhost}
              >
                {feedback.trim() ? 'Apply my feedback' : 'Try another'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function List({
  label,
  items,
  hint,
}: {
  label: string
  items: string[]
  hint?: string
}) {
  return (
    <div className="mt-3">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
        {label}
      </span>
      <ul className="mt-1 space-y-1">
        {items.map((c, i) => (
          <li key={i} className="flex gap-2 text-[11px] leading-relaxed text-muted">
            <span className="mt-[2px] text-ink">·</span>
            <span>{c}</span>
          </li>
        ))}
      </ul>
      {hint && <p className="mt-1 text-[10px] text-faint">{hint}</p>}
    </div>
  )
}

/** Kept next to the field it refines, so the affordance is where the writing is. */
export function RefineButton({
  disabled,
  active,
  onClick,
}: {
  disabled: boolean
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={
        disabled
          ? 'Write an instruction first, then this can sharpen it'
          : 'Turn this into instructions the writer can act on'
      }
      className="text-[11px] font-medium text-ink underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:text-faint disabled:no-underline"
    >
      {active ? 'Hide suggestion' : 'Improve'}
    </button>
  )
}
