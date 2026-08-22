import { useState } from 'react'
import clsx from 'clsx'
import type {
  DiffChange,
  DiffNode,
  DiffSegment,
  GraphDiff,
  VersionInfo,
} from '../../types/docos'

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

export function VersionTimeline({ versions, diff, disabled, onUndo, onRedo, onRewind, onRestore, onCompare, onCloseDiff }: Props) {
 const [pick, setPick] = useState<number[]>([])

 const togglePick = (seq: number) => {
 setPick((p) => {
 if (p.includes(seq)) return p.filter((x) => x !== seq)
 const next = [...p, seq].slice(-2)
 return next
 })
 }

 return (
 <div className="flex h-full flex-col gap-3">
 <div className="flex items-center justify-between">
 <div className="text-sm font-semibold text-ink">Timeline</div>
 <div className="flex gap-1">
 <IconBtn label="Undo" disabled={disabled} onClick={onUndo} />
 <IconBtn label="Redo" disabled={disabled} onClick={onRedo} />
 {pick.length === 2 && (
 <button
 onClick={() => onCompare(Math.min(...pick), Math.max(...pick))}
 disabled={disabled}
 className="rounded-lg bg-accent px-2 py-1 text-[11px] font-medium text-accent-fg disabled:opacity-50"
 >
 Compare {Math.min(...pick)}↔{Math.max(...pick)}
 </button>
 )}
 </div>
 </div>

 <div className="relative flex-1 space-y-1 overflow-auto pr-1">
 <div className="absolute left-[9px] top-1 bottom-1 w-px bg-line" />
 {[...versions].reverse().map((v) => (
 <div key={v.id} className="relative flex items-start gap-2 pl-6">
 <span
 className={clsx(
 'absolute left-1 top-2 h-3 w-3 rounded-full border-2',
 v.is_current
 ? 'border-ink bg-ink'
 : v.is_checkpoint
 ? 'border-emerald-500 bg-surface'
 : 'border-line-strong bg-surface',
 )}
 />
 <button
 onClick={() => togglePick(v.seq)}
 className={clsx(
 'flex-1 rounded-lg px-2 py-1.5 text-left text-xs transition-colors',
 pick.includes(v.seq) ? 'bg-ink/15' : 'hover:bg-surface-2',
 )}
 >
 <div className="flex items-center justify-between">
 <span className="font-medium text-ink ">
 v{v.seq} · {v.label}
 </span>
 {v.is_checkpoint && <span className="text-[9px] uppercase text-emerald-500">snapshot</span>}
 </div>
 <div className="text-[10px] text-faint">{new Date(v.timestamp).toLocaleString()}</div>
 </button>
 {!v.is_current && (
 <div className="flex flex-col gap-0.5">
 <MiniBtn label="Rewind" disabled={disabled} onClick={() => onRewind(v.seq)} />
 <MiniBtn label="Restore" disabled={disabled} onClick={() => onRestore(v.seq)} />
 </div>
 )}
 </div>
 ))}
 </div>

 {diff && <DiffPanel a={diff.a} b={diff.b} diff={diff.diff} onClose={onCloseDiff} />}
 </div>
 )
}

/** The compare result: counts up top, then the actual words that changed. */
function DiffPanel({ a, b, diff, onClose }: { a: number; b: number; diff: GraphDiff; onClose: () => void }) {
 const [open, setOpen] = useState(true)
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
 <div className="flex max-h-[45%] flex-col rounded-2xl border border-line bg-surface-2 text-xs">
 <div className="flex items-center justify-between gap-2 px-3 pt-3">
 <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 font-semibold text-ink">
 <span className={clsx('transition-transform', open && 'rotate-90')}>›</span>
 Diff v{a} → v{b}
 </button>
 <button onClick={onClose} className="rounded px-1 text-faint hover:text-ink" aria-label="Close diff">
 ✕
 </button>
 </div>

 <div className="flex flex-wrap gap-1 px-3 py-2">
 <Chip color="text-emerald-500" label="added" n={summary.added} />
 <Chip color="text-danger" label="removed" n={summary.removed} />
 <Chip color="text-amber-500" label="changed" n={summary.changed} />
 {(summary.words_added > 0 || summary.words_removed > 0) && (
 <span className="rounded-full bg-surface px-2 py-0.5 text-[10px] text-faint">
 +{summary.words_added} / −{summary.words_removed} words
 </span>
 )}
 </div>

 {open && (
 <div className="space-y-2 overflow-auto px-3 pb-3">
 {empty && <div className="text-[11px] text-faint">These two versions are identical.</div>}
 {diff.changed.map((c) => (
 <ChangedEntry key={c.id} change={c} />
 ))}
 {diff.added.map((n) => (
 <NodeEntry key={n.id} node={n} kind="added" />
 ))}
 {diff.removed.map((n) => (
 <NodeEntry key={n.id} node={n} kind="removed" />
 ))}
 </div>
 )}
 </div>
 )
}

function ChangedEntry({ change }: { change: DiffChange }) {
 return (
 <div className="rounded-lg border border-line bg-surface p-2">
 <EntryLabel color="text-amber-500" kind="changed" type={change.type} />
 {change.content && (
 <p className="mt-1 leading-relaxed">
 {change.content.segments.map((seg, i) => (
 <Segment key={i} seg={seg} />
 ))}
 {change.content.truncated && <span className="text-faint"> …</span>}
 </p>
 )}
 {change.style?.fields.map((f) => (
 <div key={f.field} className="mt-1 flex items-center gap-1 text-[10px] text-muted">
 <span className="text-faint">{f.field}</span>
 <s className="text-danger">{fmt(f.before)}</s>
 <span className="text-faint">→</span>
 <span className="text-emerald-500">{fmt(f.after)}</span>
 </div>
 ))}
 </div>
 )
}

function NodeEntry({ node, kind }: { node: DiffNode; kind: 'added' | 'removed' }) {
 const added = kind === 'added'
 return (
 <div className="rounded-lg border border-line bg-surface p-2">
 <EntryLabel color={added ? 'text-emerald-500' : 'text-danger'} kind={kind} type={node.type} />
 <p
 className={clsx(
 'mt-1 leading-relaxed',
 added ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-danger/15 text-danger line-through',
 )}
 >
 {node.content || <span className="text-faint italic">(no text)</span>}
 {node.truncated && <span className="text-faint"> …</span>}
 </p>
 </div>
 )
}

/** One run of words, coloured by whether it arrived, left, or stayed put. */
function Segment({ seg }: { seg: DiffSegment }) {
 if (seg.op === 'equal') return <span className="text-muted">{seg.text}</span>
 if (seg.op === 'insert')
 return <ins className="bg-emerald-500/15 text-emerald-600 no-underline dark:text-emerald-400">{seg.text}</ins>
 return <del className="bg-danger/15 text-danger">{seg.text}</del>
}

function EntryLabel({ color, kind, type }: { color: string; kind: string; type: string }) {
 return (
 <div className="flex items-center justify-between text-[9px] uppercase tracking-wide">
 <span className={color}>{kind}</span>
 <span className="text-faint">{type.replace(/_/g, ' ')}</span>
 </div>
 )
}

function Chip({ color, label, n }: { color: string; label: string; n: number }) {
 return (
 <span className={clsx('rounded-full bg-surface px-2 py-0.5 text-[10px]', color)}>
 {n} {label}
 </span>
 )
}

function fmt(value: unknown): string {
 if (value === null || value === undefined || value === '') return '—'
 return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function IconBtn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
 return (
 <button
 onClick={onClick}
 disabled={disabled}
 className="rounded-lg border border-line bg-surface-2 px-2 py-1 text-[11px] font-medium text-muted hover:bg-surface-2 disabled:opacity-50 "
 >
 {label}
 </button>
 )
}

function MiniBtn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
 return (
 <button
 onClick={onClick}
 disabled={disabled}
 className="rounded border border-line bg-surface-2 px-1.5 py-0.5 text-[9px] text-muted hover:bg-surface-2 disabled:opacity-50"
 >
 {label}
 </button>
 )
}
