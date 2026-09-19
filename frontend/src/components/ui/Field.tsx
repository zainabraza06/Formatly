import { useId, type ReactNode } from 'react'
import { cn } from '../../lib/cn'

/**
 * Label + control + hint/error, wired together by id so a screen reader reads
 * the hint and the error with the field rather than as loose text nearby.
 * The control is a render prop because it needs the generated ids.
 */
export function Field({
  label,
  hint,
  error,
  required,
  optional,
  className,
  children,
}: {
  label: string
  hint?: ReactNode
  error?: string | null
  required?: boolean
  optional?: boolean
  className?: string
  children: (props: {
    id: string
    'aria-describedby': string | undefined
    'aria-invalid': true | undefined
    'aria-required': true | undefined
  }) => ReactNode
}) {
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy = [error ? errorId : null, hint ? hintId : null]
    .filter(Boolean)
    .join(' ') || undefined

  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="flex items-baseline gap-1.5 text-sm font-medium text-ink">
        {label}
        {required && <span className="text-danger" aria-hidden>*</span>}
        {optional && <span className="text-2xs font-normal text-faint">optional</span>}
      </label>

      {children({
        id,
        'aria-describedby': describedBy,
        'aria-invalid': error ? true : undefined,
        'aria-required': required || undefined,
      })}

      {error ? (
        <p id={errorId} className="flex items-start gap-1.5 text-xs text-danger">
          <svg viewBox="0 0 16 16" fill="currentColor" className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden>
            <path fillRule="evenodd" d="M8 1.5A6.5 6.5 0 1 0 8 14.5 6.5 6.5 0 0 0 8 1.5zM7.25 4.5a.75.75 0 0 1 1.5 0v4a.75.75 0 0 1-1.5 0v-4zM8 11.75a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="text-xs leading-relaxed text-faint">{hint}</p>
      ) : null}
    </div>
  )
}
