import { useState } from 'react'
import clsx from 'clsx'
import type { GraphDiff, VersionInfo } from '../../types/docos'

interface Props {
  versions: VersionInfo[]
  diff: { a: number; b: number; diff: GraphDiff } | null
  disabled: boolean
  onUndo: () => void
  onRedo: () => void
  onRewind: (seq: number) => void
  onRestore: (seq: number) => void
  onCompare: (a: number, b: number) => void
}

export function VersionTimeline({ versions, diff, disabled, onUndo, onRedo, onRewind, onRestore, onCompare }: Props) {
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
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Timeline</div>
        <div className="flex gap-1">
          <IconBtn label="Undo" disabled={disabled} onClick={onUndo} />
          <IconBtn label="Redo" disabled={disabled} onClick={onRedo} />
          {pick.length === 2 && (
            <button
              onClick={() => onCompare(Math.min(...pick), Math.max(...pick))}
              disabled={disabled}
              className="rounded-lg bg-sky-500 px-2 py-1 text-[11px] font-semibold text-white disabled:opacity-50"
            >
              Compare {Math.min(...pick)}↔{Math.max(...pick)}
            </button>
          )}
        </div>
      </div>

      <div className="relative flex-1 space-y-1 overflow-auto pr-1">
        <div className="absolute left-[9px] top-1 bottom-1 w-px bg-neutral-200 dark:bg-neutral-800" />
        {[...versions].reverse().map((v) => (
          <div key={v.id} className="relative flex items-start gap-2 pl-6">
            <span
              className={clsx(
                'absolute left-1 top-2 h-3 w-3 rounded-full border-2',
                v.is_current
                  ? 'border-sky-400 bg-sky-400'
                  : v.is_checkpoint
                    ? 'border-emerald-400 bg-white dark:bg-neutral-950'
                    : 'border-neutral-300 bg-white dark:border-neutral-700 dark:bg-neutral-950',
              )}
            />
            <button
              onClick={() => togglePick(v.seq)}
              className={clsx(
                'flex-1 rounded-lg px-2 py-1.5 text-left text-xs transition-colors',
                pick.includes(v.seq) ? 'bg-sky-400/15' : 'hover:bg-white/5',
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-neutral-800 dark:text-neutral-100">
                  v{v.seq} · {v.label}
                </span>
                {v.is_checkpoint && <span className="text-[9px] uppercase text-emerald-500">snapshot</span>}
              </div>
              <div className="text-[10px] text-neutral-400">{new Date(v.timestamp).toLocaleString()}</div>
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

      {diff && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-xs">
          <div className="mb-1 font-semibold text-neutral-800 dark:text-neutral-100">
            Diff v{diff.a} → v{diff.b}
          </div>
          <DiffLine color="text-emerald-500" label="added" items={diff.diff.added.length} />
          <DiffLine color="text-red-500" label="removed" items={diff.diff.removed.length} />
          <DiffLine color="text-amber-500" label="changed" items={diff.diff.changed.length} />
        </div>
      )}
    </div>
  )
}

function DiffLine({ color, label, items }: { color: string; label: string; items: number }) {
  return (
    <div className={clsx('flex justify-between', color)}>
      <span>{label}</span>
      <span>{items}</span>
    </div>
  )
}

function IconBtn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] font-medium text-neutral-600 hover:bg-white/10 disabled:opacity-50 dark:text-neutral-300"
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
      className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[9px] text-neutral-500 hover:bg-white/10 disabled:opacity-50"
    >
      {label}
    </button>
  )
}
