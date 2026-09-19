import { useRef, useState } from 'react'
import { cn } from '../../lib/cn'
import { Button, Progress, Spinner } from '../ui'
import { SparkIcon, WarningIcon } from '../icons'
import type { PanelState } from '../../hooks/useDocOS'

const SUGGESTIONS = [
  'Make all headings consistent',
  'Justify every body paragraph',
  'Reformat the citations',
  'Highlight all figures',
  'Remove every horizontal line',
  'Centre every image',
]

/**
 * Where you tell the assistant what to do, and watch it do it.
 *
 * Everything it is doing is announced politely for a screen reader as well as
 * shown: the whole point of the panel is that an AI edit is never a surprise,
 * and that only works if the commentary reaches everybody.
 */
export function AICommandBar({
  panel,
  running,
  disabled,
  onRun,
}: {
  panel: PanelState
  running: boolean
  disabled: boolean
  onRun: (command: string) => void
}) {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const submit = () => {
    const command = input.trim()
    if (!command || disabled || running) return
    onRun(command)
    setInput('')
  }

  const pct = panel.progress?.total
    ? Math.round((panel.progress.done / panel.progress.total) * 100)
    : null

  return (
    <div className="flex h-full flex-col gap-3">
      {/* ── The instruction ─────────────────────────────────────────────── */}
      <div>
        <label htmlFor="ai-command" className="sr-only">
          Tell the assistant what to change
        </label>
        <div
          className={cn(
            'rounded-lg border border-line bg-surface transition-colors duration-fast',
            'focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/25',
            disabled && 'opacity-60',
          )}
        >
          <textarea
            id="ai-command"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // Enter sends; Shift+Enter is a new line, as in every chat box.
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                submit()
              }
            }}
            disabled={disabled}
            rows={2}
            placeholder={
              disabled
                ? 'Open a document first…'
                : 'e.g. Make all headings consistent'
            }
            className="w-full resize-none bg-transparent px-3 pt-2.5 text-sm text-ink outline-none placeholder:text-faint"
          />
          <div className="flex items-center justify-between gap-2 px-2 pb-2">
            <span className="pl-1 text-2xs text-faint">
              <kbd className="font-sans">Enter</kbd> to run
            </span>
            <Button
              variant="primary"
              size="sm"
              onClick={submit}
              disabled={disabled || !input.trim()}
              loading={running}
              leadingIcon={running ? undefined : <SparkIcon />}
            >
              {running ? 'Working…' : 'Run'}
            </Button>
          </div>
        </div>
      </div>

      {/* ── Suggestions ─────────────────────────────────────────────────── */}
      {!running && (
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => !disabled && onRun(s)}
              disabled={disabled}
              className={cn(
                'rounded-full border border-line bg-surface px-2.5 py-1 text-2xs text-muted',
                'transition-colors duration-fast hover:border-line-strong hover:text-ink',
                'disabled:cursor-not-allowed disabled:opacity-50',
              )}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* ── What it is doing ────────────────────────────────────────────── */}
      <div className="rounded-lg border border-line bg-surface-2/60 p-3">
        {panel.task && (
          <p className="mb-2 truncate text-2xs text-faint">
            Instruction: <span className="text-muted">{panel.task}</span>
          </p>
        )}

        <div
          data-testid="current-action"
          aria-live="polite"
          aria-atomic="true"
          className="flex items-center gap-2 text-sm font-medium text-ink"
        >
          {running && <Spinner size="sm" />}
          {panel.currentAction}
          {panel.progress?.total ? (
            <span className="ml-auto text-2xs tabular-nums text-faint">
              {panel.progress.done}/{panel.progress.total}
            </span>
          ) : null}
        </div>

        {panel.summary && <p className="mt-1 text-xs leading-relaxed text-muted">{panel.summary}</p>}

        {(running || pct !== null) && (
          <Progress value={pct} label={panel.currentAction} className="mt-2.5" />
        )}

        {panel.reading && (
          <p className="mt-2 flex items-center gap-1.5 text-2xs text-muted" aria-live="polite">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand" aria-hidden />
            {panel.reading.of
              ? `Reading the document — page ${panel.reading.page} of ${panel.reading.of}…`
              : 'Reading the document…'}
          </p>
        )}

        {panel.provider && (
          <p className="mt-2 text-2xs uppercase tracking-wide text-faint">
            via {panel.provider}{panel.source ? ` · ${panel.source}` : ''}
          </p>
        )}

        {panel.error && (
          <p role="alert" className="mt-2 flex items-start gap-1.5 rounded-md border border-danger/25 bg-danger-soft px-2 py-1.5 text-xs text-danger">
            <WarningIcon className="mt-px h-3.5 w-3.5 shrink-0" />
            {panel.error}
          </p>
        )}
      </div>

      {/* ── Plan and history ────────────────────────────────────────────── */}
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto">
        {panel.upcoming.length > 0 && (
          <Section title="Still to do">
            {panel.upcoming.map((u, i) => (
              <li key={i} className="text-muted">{u}</li>
            ))}
          </Section>
        )}

        {panel.history.length > 0 && (
          <Section title="Earlier instructions">
            {panel.history.map((h, i) => (
              <li key={i} className="border-l border-line pl-2">
                <span className="block text-ink">{h.prompt}</span>
                <span className="block text-2xs text-faint">{h.outcome}</span>
              </li>
            ))}
          </Section>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-2xs font-semibold uppercase tracking-wide text-faint">{title}</p>
      <ul className="space-y-1 text-xs">{children}</ul>
    </div>
  )
}
