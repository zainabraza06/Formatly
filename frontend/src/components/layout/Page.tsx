import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

/**
 * The page frame every screen sits in.
 *
 * The rules it encodes are not preferences; they are what the published
 * systems agree on, and screens that each invent their own width and margins
 * are what makes a product look assembled rather than designed.
 *
 *  · Two widths, not a width per screen. `wide` is 1296px including margins —
 *    Atlassian's fixed-wide, for anything you scan: a library, a dashboard, a
 *    workspace. `narrow` is 864px — their fixed-narrow, for anything you read
 *    or fill in, because a form field 1200px from the label that names it is
 *    a form nobody can follow.
 *
 *  · Margins are 16px on a phone and 32px from 1024px up, per the same grid.
 *    They are the page's margins, so every screen's content starts on the
 *    same vertical line.
 *
 *  · Vertical rhythm comes off the 8px scale: 24px from the header to the
 *    content, 32px between sections. Generous, and then taken away — which is
 *    the opposite order from how it usually goes wrong.
 *
 * `fill` is for a screen that owns the viewport rather than scrolling inside
 * it — the editor — so it gets the frame without the trailing space.
 */
export function Page({
  width = 'wide',
  fill,
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement> & {
  width?: 'wide' | 'narrow'
  fill?: boolean
  children: ReactNode
}) {
  return (
    <div
      className={cn(
        'mx-auto w-full',
        width === 'wide' ? 'max-w-[81rem]' : 'max-w-[54rem]',
        // `fill` deliberately does NOT grow: a screen that owns the viewport
        // states its own height, and flex-1 inside a content-sized parent
        // grows to fit its content instead — which is how a document taller
        // than the window pushed the page controls off the bottom of it.
        fill ? 'flex min-h-0 flex-col gap-4' : 'space-y-8',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

/**
 * A page's title, what it is for, and the one action it exists to offer.
 *
 * Hierarchy here is size and weight, not colour and not a box: the title is
 * the largest thing on the screen, the sentence under it is the smallest, and
 * everything between them is body text. De-emphasising the description is
 * what makes the title read as a title.
 */
export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-x-4 gap-y-3', className)}>
      <div className="min-w-0">
        <h1 className="text-2xl text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

/**
 * A titled part of a page: its name and purpose above the thing itself, on
 * the page's own left edge. Sections read as one column that way, where a
 * heading inside each card reads as a stack of unrelated boxes.
 */
export function Section({
  title,
  description,
  actions,
  children,
  className,
}: {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={className}>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 className="text-base font-medium text-ink">{title}</h2>
          {description && <p className="mt-1 text-sm text-muted">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {children}
    </section>
  )
}
