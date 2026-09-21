import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { cn } from '../../lib/cn'
import { Badge, Button, EmptyState, Spinner } from '../ui'
import { ClockIcon, CloseIcon, UndoIcon } from '../icons'
import type {
  DiffChange,
  DiffNode,
  DiffSegment,
  GraphDiff,
  VersionInfo,
} from '../../types/docos'

/** Long enough to register as "it is doing the thing", short enough not to
 *  feel like a delay that was added on purpose. */
const MIN_VISIBLE_MS = 500

interface Props {
  versions: VersionInfo[]
  diff: { a: number; b: number; diff: GraphDiff } | null
  disabled: boolean
  onUndo: () => void
  onRedo: () => void
  onRewind: (seq: number) => void
  onRestore: (seq: number) => void
  onCompare: (a: number, b: number) => void
  onCloseDiff: () => void
}

/**
 * Every version of the document, newest first, and what changed between any
 * two of them. Nothing the assistant does is lost: this is where it goes.
 */
export function VersionTimeline({
  versions, diff, disabled, onUndo, onRedo, onRewind, onRestore, onCompare, onCloseDiff,
}: Props) {
  const [picked, setPicked] = useState<number[]>([])
  const reduced = useReducedMotion()
  // What was asked for, so the control that was pressed can say it is working.
  const [asked, setAsked] = useState<{ kind: string; seq?: number } | null>(null)
  // Held for a moment even after the engine has finished. Restoring a version
  // locally takes about eighty milliseconds, and an indicator shown for eighty
  // milliseconds is one nobody sees: the button flickers and the reader is left
  // wondering whether their click registered at all.
  const [holding, setHolding] = useState(false)
  const holdTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (holdTimer.current) window.clearTimeout(holdTimer.current)
  }, [])

  /** Say what is being done, do it, and keep saying it long enough to read. */
  const start = (what: { kind: string; seq?: number }, run: () => void) => {
    setAsked(what)
    setHolding(true)
    if (holdTimer.current) window.clearTimeout(holdTimer.current)
    holdTimer.current = window.setTimeout(() => setHolding(false), MIN_VISIBLE_MS)
    run()
  }

  const pending = asked && (disabled || holding) ? asked : null

  const togglePick = (seq: number) => {
    setPicked((p) => (p.includes(seq) ? p.filter((x) => x !== seq) : [...p, seq].slice(-2)))
  }

  if (!versions.length) {
    return (
      <EmptyState
        icon={<ClockIcon className="h-5 w-5" />}
        title="No history yet"
        description="Every instruction you give the assistant is saved as a version here, and any of them can be restored."
        className="py-8"
      />
    )
  }

  return (
    <div
      className="flex h-full min-h-0 flex-col gap-3"
      // What the panel believes it is doing, so a test can read it without
      // matching prose.
      data-pending={pending?.kind ?? 'none'}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex gap-1.5">
          <Button
            variant="secondary" size="sm" disabled={disabled}
            onClick={() => start({ kind: 'undo' }, onUndo)}
            loading={pending?.kind === 'undo'}
            leadingIcon={pending?.kind === 'undo' ? undefined : <UndoIcon />}
          >
            {pending?.kind === 'undo' ? 'Undoing…' : 'Undo'}
          </Button>
          <Button
            variant="secondary" size="sm" disabled={disabled}
            onClick={() => start({ kind: 'redo' }, onRedo)}
            loading={pending?.kind === 'redo'}
          >
            {pending?.kind === 'redo' ? 'Redoing…' : 'Redo'}
          </Button>
        </div>

        {picked.length === 2 && (
          <Button
            variant="primary"
            size="sm"
            disabled={disabled}
            loading={pending?.kind === 'compare'}
            onClick={() => start(
              { kind: 'compare' },
              () => onCompare(Math.min(...picked), Math.max(...picked)),
            )}
          >
            Compare v{Math.min(...picked)} → v{Math.max(...picked)}
          </Button>
        )}
      </div>

      {pending && (pending.kind === 'rewind' || pending.kind === 'restore') && (
        <p className="flex items-center gap-1.5 rounded-md border border-line bg-surface-2/60 px-2 py-1.5 text-2xs text-muted" role="status">
          <Spinner size="sm" />
          {pending.kind === 'rewind' ? 'Rewinding to' : 'Restoring'} v{pending.seq}…
        </p>
      )}

      {pending?.kind === 'compare' && (
        <p className="flex items-center gap-1.5 rounded-md border border-line bg-surface-2/60 px-2 py-1.5 text-2xs text-muted" role="status">
          <Spinner size="sm" />
          Comparing…
        </p>
      )}

      {!pending && picked.length === 1 && (
        <p className="text-2xs text-faint">
          Pick a second version to compare it with v{picked[0]}.
        </p>
      )}

      <ol className="relative min-h-0 flex-1 space-y-0.5 overflow-y-auto pr-1">
        <span className="absolute bottom-2 left-[7px] top-2 w-px bg-line" aria-hidden />

        {[...versions].reverse().map((v, index) => (
          <motion.li
            key={v.id}
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.26,
              delay: Math.min(index * 0.03, 0.2),
              ease: [0.16, 1, 0.3, 1],
            }}
            className={cn(
              'relative flex items-start gap-2 rounded-md pl-5 transition-colors',
              pending?.seq === v.seq && 'bg-brand-soft/60',
            )}
          >
            <span
              className={cn(
                'absolute left-0 top-2.5 h-3.5 w-3.5 rounded-full border-2 bg-surface',
                v.is_current ? 'border-brand bg-brand' : v.is_checkpoint ? 'border-success' : 'border-line-strong',
              )}
              aria-hidden
            />

            <button
              type="button"
              onClick={() => togglePick(v.seq)}
              aria-pressed={picked.includes(v.seq)}
              className={cn(
                'min-w-0 flex-1 rounded-sm px-2 py-1.5 text-left transition-colors duration-fast',
                picked.includes(v.seq) ? 'bg-brand-soft' : 'hover:bg-surface-2',
              )}
            >
              <span className="flex items-center gap-1.5">
                <span className="truncate text-xs font-medium text-ink">
                  v{v.seq} · {v.label}
                </span>
                {v.is_current && <Badge tone="brand">current</Badge>}
                {v.is_checkpoint && !v.is_current && <Badge tone="success">snapshot</Badge>}
              </span>
              <span className="mt-0.5 block text-2xs text-faint">
                {new Date(v.timestamp).toLocaleString()}
              </span>
            </button>

            {!v.is_current && (
              <div className="flex shrink-0 flex-col gap-0.5">
                <MiniButton
                  label={pending?.kind === 'rewind' && pending.seq === v.seq ? 'Rewinding…' : 'Rewind'}
                  title={`Rewind to version ${v.seq}`}
                  disabled={disabled}
                  busy={pending?.kind === 'rewind' && pending.seq === v.seq}
                  onClick={() => start({ kind: 'rewind', seq: v.seq }, () => onRewind(v.seq))}
                />
                <MiniButton
                  label={pending?.kind === 'restore' && pending.seq === v.seq ? 'Restoring…' : 'Restore'}
                  title={`Restore version ${v.seq}`}
                  disabled={disabled}
                  busy={pending?.kind === 'restore' && pending.seq === v.seq}
                  onClick={() => start({ kind: 'restore', seq: v.seq }, () => onRestore(v.seq))}
                />
              </div>
            )}
          </motion.li>
        ))}
      </ol>

      {/* The comparison slides up from the bottom of the panel, where it
          belongs to the timeline above it. */}
      <AnimatePresence>
        {diff && (
          <motion.div
            key={`${diff.a}-${diff.b}`}
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: 12 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            className="flex min-h-0 flex-col"
          >
            <DiffPanel a={diff.a} b={diff.b} diff={diff.diff} onClose={onCloseDiff} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/** The compare result: counts up top, then the actual words that changed. */
function DiffPanel({ a, b, diff, onClose }: { a: number; b: number; diff: GraphDiff; onClose: () => void }) {
  const summary = diff.summary ?? {
    added: diff.added.length,
    removed: diff.removed.length,
    changed: diff.changed.length,
    text_changed: diff.changed.filter((c) => c.content).length,
    style_changed: diff.changed.filter((c) => c.style).length,
    words_added: 0,
    words_removed: 0,
  }
  const empty = summary.added + summary.removed + summary.changed === 0

  return (
    <section
      aria-label={`Differences between version ${a} and version ${b}`}
      className="flex max-h-[45%] shrink-0 flex-col rounded-lg border border-line bg-surface-2/60"
    >
      <header className="flex items-center justify-between gap-2 px-3 py-2">
        <h3 className="text-xs font-semibold text-ink">What changed, v{a} → v{b}</h3>
        <Button
          variant="ghost" size="sm" iconOnly
          aria-label="Close the comparison"
          onClick={onClose}
          leadingIcon={<CloseIcon className="h-3.5 w-3.5" />}
        />
      </header>

      <div className="flex flex-wrap gap-1 px-3 pb-2">
        <Badge tone="success">{summary.added} added</Badge>
        <Badge tone="danger">{summary.removed} removed</Badge>
        <Badge tone="warning">{summary.changed} changed</Badge>
        {(summary.words_added > 0 || summary.words_removed > 0) && (
          <Badge>+{summary.words_added} / −{summary.words_removed} words</Badge>
        )}
      </div>

      <div className="min-h-0 space-y-2 overflow-y-auto px-3 pb-3 text-xs">
        {empty && <p className="text-xs text-faint">These two versions are identical.</p>}
        {diff.changed.map((c) => <ChangedEntry key={c.id} change={c} />)}
        {diff.added.map((n) => <NodeEntry key={n.id} node={n} kind="added" />)}
        {diff.removed.map((n) => <NodeEntry key={n.id} node={n} kind="removed" />)}
      </div>
    </section>
  )
}

function ChangedEntry({ change }: { change: DiffChange }) {
  return (
    <div className="rounded-md border border-line bg-surface p-2">
      <EntryLabel tone="text-warning" kind="changed" type={change.type} />
      {change.content && (
        <p className="mt-1 leading-relaxed">
          {change.content.segments.map((seg, i) => <Segment key={i} seg={seg} />)}
          {change.content.truncated && <span className="text-faint"> …</span>}
        </p>
      )}
      {change.style?.fields.map((f) => (
        <div key={f.field} className="mt-1 flex flex-wrap items-center gap-1 text-2xs text-muted">
          <span className="text-faint">{f.field}</span>
          <s className="text-danger">{fmt(f.before)}</s>
          <span className="text-faint" aria-hidden>→</span>
          <span className="text-success">{fmt(f.after)}</span>
        </div>
      ))}
    </div>
  )
}

function NodeEntry({ node, kind }: { node: DiffNode; kind: 'added' | 'removed' }) {
  const added = kind === 'added'
  return (
    <div className="rounded-md border border-line bg-surface p-2">
      <EntryLabel tone={added ? 'text-success' : 'text-danger'} kind={kind} type={node.type} />
      <p
        className={cn(
          'mt-1 rounded-sm px-1 leading-relaxed',
          added ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger line-through',
        )}
      >
        {node.content || <span className="italic text-faint">(no text)</span>}
        {node.truncated && <span className="text-faint"> …</span>}
      </p>
    </div>
  )
}

/** One run of words, coloured by whether it arrived, left, or stayed put. */
function Segment({ seg }: { seg: DiffSegment }) {
  if (seg.op === 'equal') return <span className="text-muted">{seg.text}</span>
  if (seg.op === 'insert') {
    return <ins className="rounded-sm bg-success/10 px-0.5 text-success no-underline">{seg.text}</ins>
  }
  return <del className="rounded-sm bg-danger/10 px-0.5 text-danger">{seg.text}</del>
}

function EntryLabel({ tone, kind, type }: { tone: string; kind: string; type: string }) {
  return (
    <div className="flex items-center justify-between text-2xs uppercase tracking-wide">
      <span className={tone}>{kind}</span>
      <span className="text-faint">{type.replace(/_/g, ' ')}</span>
    </div>
  )
}

function MiniButton({
  label, title, onClick, disabled, busy,
}: {
  label: string
  title: string
  onClick: () => void
  disabled: boolean
  busy?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-busy={busy || undefined}
      className={cn(
        'flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-2xs transition-colors duration-fast',
        'disabled:cursor-not-allowed',
        busy
          // The one that was pressed stays legible while the rest fade: which
          // button you clicked is the thing you want confirmed.
          ? 'border-brand/40 bg-brand-soft text-brand-ink opacity-100'
          : 'border-line bg-surface text-muted hover:border-line-strong hover:text-ink disabled:opacity-50',
      )}
    >
      {busy && <Spinner size="sm" />}
      {label}
    </button>
  )
}

function fmt(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}
