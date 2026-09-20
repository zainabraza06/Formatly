import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { cn } from '../../lib/cn'
import { CheckIcon, SparkIcon, UndoIcon } from '../icons'

const INSTRUCTION = 'Make all headings consistent'
const EASE = [0.16, 1, 0.3, 1] as const

/** The four moments of using the thing, which is what the loop below plays. */
type Phase = 'idle' | 'typing' | 'working' | 'done'

/**
 * The editor, drawn rather than photographed — and running.
 *
 * A screenshot goes stale the first time a button moves, and a still picture of
 * a product whose whole point is watching an instruction take effect shows the
 * least interesting second of it. So this plays the loop: an instruction is
 * typed, the headings it names change one at a time, and the result arrives
 * with the offer to keep or undo it. It is the real sequence, at the real
 * pace, built from the same tokens as the app.
 *
 * With the system set to less movement it holds the finished state instead —
 * the same information, no motion.
 */
export function ProductMock({ className }: { className?: string }) {
  const reduced = useReducedMotion()
  const [phase, setPhase] = useState<Phase>(reduced ? 'done' : 'idle')
  const [typed, setTyped] = useState(reduced ? INSTRUCTION : '')
  const [changed, setChanged] = useState(reduced ? 3 : 0)

  useEffect(() => {
    if (reduced) return
    let cancelled = false
    const timers: number[] = []
    const wait = (ms: number) => new Promise<void>((r) => timers.push(window.setTimeout(r, ms)))

    const play = async () => {
      while (!cancelled) {
        setPhase('idle'); setTyped(''); setChanged(0)
        await wait(900)
        if (cancelled) return

        setPhase('typing')
        for (let i = 1; i <= INSTRUCTION.length; i += 1) {
          if (cancelled) return
          setTyped(INSTRUCTION.slice(0, i))
          // Uneven, the way typing is. A perfectly even crawl reads as a
          // machine printing, not a person asking for something.
          await wait(i % 7 === 0 ? 90 : 34)
        }
        await wait(420)
        if (cancelled) return

        setPhase('working')
        for (let n = 1; n <= 3; n += 1) {
          await wait(520)
          if (cancelled) return
          setChanged(n)
        }
        await wait(300)
        if (cancelled) return

        setPhase('done')
        await wait(3400)
      }
    }

    void play()
    return () => {
      cancelled = true
      timers.forEach(window.clearTimeout)
    }
  }, [reduced])

  const working = phase === 'working'
  const done = phase === 'done'

  return (
    <div
      role="img"
      aria-label="The Formatly editor: an instruction reading “Make all headings consistent” is typed into the assistant, the document's headings change one by one, and a bar offers to keep or undo the change."
      className={cn('overflow-hidden rounded-xl border border-line bg-surface', className)}
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
          <motion.span
            className="h-1.5 w-1.5 rounded-full bg-success"
            animate={reduced ? {} : { opacity: [1, 0.35, 1] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
          />
          Live
        </span>
      </div>

      <div className="grid gap-px bg-line sm:grid-cols-[minmax(0,1fr)_38%]">
        {/* ── The document ─────────────────────────────────────────────── */}
        <div className="doc-desk p-3 sm:p-4">
          <div className="mx-auto max-w-sm rounded-sm bg-white p-4 shadow-sm">
            <div className="h-2 w-2/3 rounded-full bg-slate-800" />
            <div className="mt-1.5 h-1.5 w-1/3 rounded-full bg-slate-300" />

            <div className="mt-4 space-y-1.5">
              <Line w="w-full" /><Line w="w-11/12" /><Line w="w-4/5" />
            </div>

            <Heading index={1} changed={changed} reduced={reduced} width="w-1/2" />
            <div className="mt-2 space-y-1.5">
              <Line w="w-full" /><Line w="w-full" /><Line w="w-3/5" />
            </div>

            <Heading index={2} changed={changed} reduced={reduced} width="w-2/5" />
            <div className="mt-2 space-y-1.5">
              <Line w="w-full" /><Line w="w-4/6" />
            </div>

            <Heading index={3} changed={changed} reduced={reduced} width="w-1/3" />
            <div className="mt-2 space-y-1.5">
              <Line w="w-5/6" />
            </div>
          </div>
        </div>

        {/* ── The assistant ────────────────────────────────────────────── */}
        <div className="flex flex-col gap-2.5 bg-surface p-3">
          <div className="rounded-md border border-line bg-surface-2/60 p-2">
            <p className="text-2xs text-faint">You</p>
            <p className="mt-0.5 min-h-[1.25rem] text-xs font-medium text-ink">
              {typed}
              {phase === 'typing' && (
                <motion.span
                  className="ml-px inline-block h-3 w-px translate-y-0.5 bg-ink"
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 0.9, repeat: Infinity }}
                />
              )}
            </p>
          </div>

          <AnimatePresence mode="wait">
            {(working || done) && (
              <motion.div
                key="progress"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: EASE }}
                className="rounded-md border border-line p-2"
              >
                <p className="flex items-center gap-1.5 text-xs font-medium text-ink">
                  <span className="h-1.5 w-1.5 rounded-full bg-brand" aria-hidden />
                  {done ? 'Formatted 3 headings' : `Formatting heading ${Math.max(changed, 1)} of 3…`}
                </p>
                <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-line">
                  <motion.div
                    className="h-full rounded-full bg-brand"
                    animate={{ width: `${(changed / 3) * 100}%` }}
                    transition={{ duration: 0.45, ease: EASE }}
                  />
                </div>
                <p className="mt-1.5 text-2xs text-faint">Inter Semibold 14pt · spacing 12pt before</p>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {done && (
              <motion.div
                key="review"
                initial={{ opacity: 0, y: 8, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3, ease: EASE }}
                className="rounded-md border border-brand/25 bg-brand-soft p-2"
              >
                <p className="flex items-center gap-1.5 text-xs font-medium text-ink">
                  <SparkIcon className="h-3.5 w-3.5 text-brand-ink" />
                  3 headings changed
                </p>
                <div className="mt-2 flex gap-1.5">
                  <span className="flex items-center gap-1 rounded-sm bg-brand px-2 py-0.5 text-2xs font-medium text-brand-fg">
                    <CheckIcon className="h-3 w-3" /> Keep
                  </span>
                  <span className="flex items-center gap-1 rounded-sm border border-line bg-surface px-2 py-0.5 text-2xs text-muted">
                    <UndoIcon className="h-3 w-3" /> Undo
                  </span>
                  <span className="rounded-sm px-2 py-0.5 text-2xs text-muted">See what changed</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="mt-auto flex items-center gap-2 rounded-md border border-line px-2 py-1.5 text-2xs text-faint">
            <span className="flex-1">Tell the assistant what to change…</span>
            <span className="flex h-5 w-5 items-center justify-center rounded-sm bg-brand text-brand-fg">
              <SparkIcon className="h-3 w-3" />
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

/** A heading in the mock page, which changes when the instruction reaches it. */
function Heading({
  index, changed, reduced, width,
}: { index: number; changed: number; reduced: boolean | null; width: string }) {
  const isChanged = changed >= index

  return (
    <motion.div
      className={cn('mt-4 rounded-sm px-1 py-0.5', isChanged ? 'bg-indigo-100' : 'bg-transparent')}
      animate={
        reduced || !isChanged
          ? {}
          : { scale: [1, 1.02, 1] }
      }
      transition={{ duration: 0.4, ease: EASE }}
    >
      <motion.div
        className={cn('h-2 rounded-full', isChanged ? 'bg-indigo-500' : 'bg-slate-400', width)}
        animate={{ opacity: isChanged ? 1 : 0.75 }}
        transition={{ duration: 0.3 }}
      />
    </motion.div>
  )
}

function Dot() {
  return <span className="h-2 w-2 rounded-full bg-line-strong" />
}

function Line({ w }: { w: string }) {
  return <div className={cn('h-1.5 rounded-full bg-slate-200', w)} />
}
