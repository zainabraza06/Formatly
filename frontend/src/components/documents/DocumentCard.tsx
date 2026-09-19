import { cn } from '../../lib/cn'
import { Badge, Dropdown, Spinner, type MenuItem } from '../ui'
import {
  ComposeIcon, CopyIcon, DownloadIcon, EditorIcon, FileIcon, LayersIcon, MoreIcon, TrashIcon,
} from '../icons'
import { formatDate, type DocumentItem } from '../../lib/documents'

/**
 * One document in the library. The whole face opens it; everything else lives
 * in the menu, so the card has exactly one obvious click and a place to look
 * for the rest.
 */
export function DocumentCard({
  doc,
  busy,
  onOpen,
  onExport,
  onDuplicate,
  onDelete,
}: {
  doc: DocumentItem
  /** What this card is currently doing, shown in place of its metadata. */
  busy?: string | null
  onOpen: () => void
  onExport: (format: 'docx' | 'pdf') => void
  onDuplicate?: () => void
  onDelete?: () => void
}) {
  const generated = doc.source === 'generated'

  const menu: MenuItem[] = [
    {
      id: 'open',
      label: generated ? 'Open a copy in the editor' : 'Open in editor',
      icon: <EditorIcon />,
      onSelect: onOpen,
    },
    { id: 'docx', label: 'Download DOCX', icon: <DownloadIcon />, onSelect: () => onExport('docx') },
    { id: 'pdf', label: 'Download PDF', icon: <DownloadIcon />, onSelect: () => onExport('pdf') },
    ...(onDuplicate
      ? [{ id: 'duplicate', label: 'Duplicate', icon: <CopyIcon />, onSelect: onDuplicate }]
      : []),
    ...(onDelete
      ? [{ id: 'delete', label: 'Delete', icon: <TrashIcon />, destructive: true, onSelect: onDelete }]
      : []),
  ]

  return (
    <div
      className={cn(
        'group relative flex flex-col rounded-lg border border-line bg-surface p-4 shadow-xs',
        'transition-[border-color,box-shadow] duration-fast ease-out',
        'hover:border-line-strong hover:shadow-sm',
        'focus-within:border-brand/40 focus-within:shadow-sm',
        busy && 'opacity-70',
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-md border',
            generated
              ? 'border-brand/20 bg-brand-soft text-brand-ink'
              : 'border-line bg-surface-2 text-muted',
          )}
          aria-hidden
        >
          {generated ? <ComposeIcon /> : <FileIcon />}
        </span>

        <div className="min-w-0 flex-1">
          {/* The stretched link makes the whole card clickable while keeping
              one focusable element with a real accessible name. */}
          <button
            type="button"
            onClick={onOpen}
            disabled={Boolean(busy)}
            className="text-left after:absolute after:inset-0 after:content-[''] focus:outline-none"
          >
            <span className="line-clamp-2 text-sm font-medium text-ink">
              {doc.title}
            </span>
          </button>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-2xs text-faint">
            {busy ? (
              <span className="flex items-center gap-1.5 text-muted">
                <Spinner size="sm" /> {busy}
              </span>
            ) : (
              <>
                {doc.createdAt && <span>{formatDate(doc.createdAt)}</span>}
                {doc.versions !== undefined && (
                  <span className="flex items-center gap-1">
                    <LayersIcon className="h-3 w-3" />
                    {doc.versions} {doc.versions === 1 ? 'version' : 'versions'}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-2">
        <Badge tone={generated ? 'brand' : 'neutral'}>
          {generated ? doc.stylePreset || 'Generated' : 'Upload'}
        </Badge>

        {/* Above the stretched link, so the menu is clickable. */}
        <div className="relative z-10">
          <Dropdown
            label={`Actions for ${doc.title}`}
            items={menu}
            triggerVariant="ghost"
            triggerSize="sm"
            triggerIcon={<MoreIcon />}
            disabled={Boolean(busy)}
          />
        </div>
      </div>
    </div>
  )
}

/** The card's shape while the library is loading. */
export function DocumentCardSkeleton() {
  return (
    <div className="rounded-lg border border-line bg-surface p-4 shadow-xs" aria-hidden>
      <div className="flex items-start gap-3">
        <div className="h-9 w-9 shrink-0 animate-pulse rounded-md bg-surface-2" />
        <div className="flex-1 space-y-2">
          <div className="h-3.5 w-4/5 animate-pulse rounded-sm bg-surface-2" />
          <div className="h-3 w-2/5 animate-pulse rounded-sm bg-surface-2" />
        </div>
      </div>
      <div className="mt-4 h-5 w-20 animate-pulse rounded-sm bg-surface-2" />
    </div>
  )
}
