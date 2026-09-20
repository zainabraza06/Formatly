import { motion, useReducedMotion } from 'framer-motion'
import { cn } from '../../lib/cn'
import { CheckIcon } from '../icons'

export interface Step {
  id: string
  label: string
  /** One line saying what this step is for, shown for the current step. */
  hint?: string
}

/**
 * Where you are in the flow, and what is left. Steps already completed are
 * buttons — going back to change the material is the normal thing to do, and
 * hiding it behind the browser's back button is how people lose their work.
 */
export function Stepper({
  steps,
  current,
  furthest,
  onGo,
  className,
}: {
  steps: Step[]
  current: number
  /** The furthest step reached, which is as far back as anyone may jump. */
  furthest: number
  onGo: (index: number) => void
  className?: string
}) {
  const reduced = useReducedMotion()

  return (
    <nav aria-label="Progress" className={className}>
      <ol className="flex flex-wrap items-center gap-x-1 gap-y-2">
        {steps.map((step, i) => {
          const done = i < current
          const active = i === current
          const reachable = i <= furthest

          return (
            <li key={step.id} className="flex items-center">
              <button
                type="button"
                disabled={!reachable || active}
                onClick={() => onGo(i)}
                aria-current={active ? 'step' : undefined}
                className={cn(
                  'flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors duration-fast',
                  active && 'font-medium text-ink',
                  !active && reachable && 'text-muted hover:bg-surface-2 hover:text-ink',
                  !reachable && 'cursor-not-allowed text-faint',
                )}
              >
                <motion.span
                  className={cn(
                    'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-2xs font-semibold',
                    done && 'border-brand bg-brand text-brand-fg',
                    active && 'border-brand bg-brand-soft text-brand-ink',
                    !done && !active && 'border-line text-faint',
                  )}
                  // A step that has just been completed is worth a beat: it is
                  // the only feedback that pressing Continue did anything.
                  animate={reduced ? {} : { scale: done ? [1, 1.15, 1] : 1 }}
                  transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
                  aria-hidden
                >
                  {done ? <CheckIcon className="h-3.5 w-3.5" /> : i + 1}
                </motion.span>
                <span className="hidden sm:inline">{step.label}</span>
                <span className="sr-only sm:hidden">{step.label}</span>
              </button>

              {i < steps.length - 1 && (
                // The connector fills towards the step it leads to, so the
                // flow reads as progress rather than as four separate lights.
                <span aria-hidden className="relative mx-1 h-px w-4 overflow-hidden bg-line sm:w-8">
                  <motion.span
                    className="absolute inset-y-0 left-0 bg-brand"
                    initial={false}
                    animate={{ width: done ? '100%' : '0%' }}
                    transition={{ duration: reduced ? 0 : 0.4, ease: [0.16, 1, 0.3, 1] }}
                  />
                </span>
              )}
            </li>
          )
        })}
      </ol>

      {steps[current]?.hint && (
        <p className="mt-2 text-sm text-muted sm:hidden">{steps[current].hint}</p>
      )}
    </nav>
  )
}
