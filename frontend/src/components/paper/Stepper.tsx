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
                <span
                  className={cn(
                    'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-2xs font-semibold',
                    done && 'border-brand bg-brand text-brand-fg',
                    active && 'border-brand bg-brand-soft text-brand-ink',
                    !done && !active && 'border-line text-faint',
                  )}
                  aria-hidden
                >
                  {done ? <CheckIcon className="h-3.5 w-3.5" /> : i + 1}
                </span>
                <span className="hidden sm:inline">{step.label}</span>
                <span className="sr-only sm:hidden">{step.label}</span>
              </button>

              {i < steps.length - 1 && (
                <span
                  aria-hidden
                  className={cn('mx-1 h-px w-4 sm:w-8', done ? 'bg-brand' : 'bg-line')}
                />
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
