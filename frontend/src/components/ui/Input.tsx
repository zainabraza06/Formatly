import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

const CONTROL =
  'w-full rounded-md border border-line bg-surface text-ink placeholder:text-faint ' +
  'transition-colors duration-fast ease-out ' +
  'focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/25 ' +
  'disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-muted ' +
  'aria-[invalid=true]:border-danger aria-[invalid=true]:focus:ring-danger/25'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & {
  leadingIcon?: ReactNode
  trailingSlot?: ReactNode
}>(function Input({ className, leadingIcon, trailingSlot, ...rest }, ref) {
  const control = (
    <input
      ref={ref}
      className={cn(
        CONTROL,
        'h-9 px-3 text-sm',
        leadingIcon && 'pl-9',
        trailingSlot && 'pr-9',
        className,
      )}
      {...rest}
    />
  )

  if (!leadingIcon && !trailingSlot) return control

  return (
    <div className="relative">
      {leadingIcon && (
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" aria-hidden>
          {leadingIcon}
        </span>
      )}
      {control}
      {trailingSlot && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-faint">{trailingSlot}</span>
      )}
    </div>
  )
})

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...rest }, ref) {
    return (
      <textarea
        ref={ref}
        className={cn(CONTROL, 'resize-y px-3 py-2 text-sm leading-relaxed', className)}
        {...rest}
      />
    )
  },
)

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...rest }, ref) {
    return (
      <div className="relative">
        <select
          ref={ref}
          className={cn(CONTROL, 'h-9 appearance-none pl-3 pr-9 text-sm', className)}
          {...rest}
        >
          {children}
        </select>
        <svg
          viewBox="0 0 20 20" fill="currentColor" aria-hidden
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint"
        >
          <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06z" clipRule="evenodd" />
        </svg>
      </div>
    )
  },
)
