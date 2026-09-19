import { cn } from '../../lib/cn'
import { Tooltip } from '../ui'

export type Connection = 'live' | 'connecting' | 'offline'

const COPY: Record<Connection, { label: string; detail: string; dot: string; text: string }> = {
  live: {
    label: 'Live',
    detail: 'Connected. You can watch the assistant work, step by step.',
    dot: 'bg-success',
    text: 'text-success',
  },
  connecting: {
    label: 'Reconnecting',
    detail: 'The live connection dropped and is being retried. Instructions still run — you just will not see each step until it is back.',
    dot: 'bg-warning animate-pulse',
    text: 'text-warning',
  },
  offline: {
    label: 'Offline',
    detail: 'No live connection. Instructions are sent as ordinary requests, and the result appears when it is finished.',
    dot: 'bg-faint',
    text: 'text-muted',
  },
}

/**
 * Whether the document is following along live.
 *
 * This used to be a 6px dot reading "live" or "offline", with no reconnect
 * behind it — so a dropped socket looked permanent and said nothing about what
 * still worked. It names the state, and the tooltip says what it means for the
 * next instruction.
 */
export function ConnectionBadge({ state, className }: { state: Connection; className?: string }) {
  const copy = COPY[state]

  return (
    <Tooltip content={copy.detail}>
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded-sm border border-line bg-surface px-1.5 py-0.5 text-2xs font-medium',
          copy.text,
          className,
        )}
      >
        <span className={cn('h-1.5 w-1.5 rounded-full', copy.dot)} aria-hidden />
        {copy.label}
        <span className="sr-only">. {copy.detail}</span>
      </span>
    </Tooltip>
  )
}
