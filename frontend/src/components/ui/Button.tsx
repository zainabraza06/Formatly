import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'
import { cn } from '../../lib/cn'
import { Spinner } from './Spinner'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'subtle'
export type ButtonSize = 'sm' | 'md' | 'lg'

/** One primary action per screen — that is what `primary` is for. Everything
 *  else on the screen is `secondary`, `ghost` or `subtle`. */
const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-brand text-brand-fg shadow-sm hover:bg-brand-hover active:bg-brand-hover ' +
    'disabled:hover:bg-brand',
  secondary:
    'border border-line bg-surface text-ink shadow-xs hover:bg-surface-2 ' +
    'hover:border-line-strong disabled:hover:bg-surface',
  ghost:
    'text-muted hover:bg-surface-2 hover:text-ink disabled:hover:bg-transparent',
  subtle:
    'bg-surface-2 text-ink hover:bg-line disabled:hover:bg-surface-2',
  danger:
    'bg-danger text-white shadow-sm hover:opacity-90 disabled:hover:opacity-100',
}

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 gap-1.5 rounded-md px-2.5 text-xs',
  md: 'h-9 gap-2 rounded-md px-3.5 text-sm',
  lg: 'h-11 gap-2 rounded-lg px-5 text-base',
}

const ICON_SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 w-8 rounded-md',
  md: 'h-9 w-9 rounded-md',
  lg: 'h-11 w-11 rounded-lg',
}

const BASE =
  'inline-flex shrink-0 items-center justify-center whitespace-nowrap font-medium ' +
  'transition-colors duration-fast ease-out ' +
  'disabled:cursor-not-allowed disabled:opacity-50'

interface Shared {
  variant?: ButtonVariant
  size?: ButtonSize
  /** Renders a square button. Pass `aria-label` — there is no text to read. */
  iconOnly?: boolean
  /** Swaps the leading icon for a spinner and blocks the click. */
  loading?: boolean
  leadingIcon?: ReactNode
  trailingIcon?: ReactNode
  fullWidth?: boolean
}

export interface ButtonProps
  extends Shared, Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  children?: ReactNode
}

function classesFor(
  { variant = 'secondary', size = 'md', iconOnly, fullWidth }: Shared,
  className?: string,
) {
  return cn(
    BASE,
    VARIANTS[variant],
    iconOnly ? ICON_SIZES[size] : SIZES[size],
    fullWidth && 'w-full',
    className,
  )
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, size = 'md', iconOnly, loading, leadingIcon, trailingIcon, fullWidth,
    className, children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={classesFor({ variant, size, iconOnly, fullWidth }, className)}
      {...rest}
    >
      {loading ? <Spinner size={size === 'lg' ? 'md' : 'sm'} /> : leadingIcon}
      {children}
      {!loading && trailingIcon}
    </button>
  )
})

export interface ButtonLinkProps extends Shared, Omit<LinkProps, 'className'> {
  className?: string
}

/** The same button, when the action is "go somewhere". */
export function ButtonLink({
  variant, size = 'md', iconOnly, leadingIcon, trailingIcon, fullWidth,
  className, children, ...rest
}: ButtonLinkProps) {
  return (
    <Link className={classesFor({ variant, size, iconOnly, fullWidth }, className)} {...rest}>
      {leadingIcon}
      {children}
      {trailingIcon}
    </Link>
  )
}
