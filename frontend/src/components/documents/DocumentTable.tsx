import { cn } from '../../lib/cn'
import { formatDate, SORT_LABELS, type DocumentItem, type SortKey } from '../../lib/documents'
import { Dropdown, Spinner, type MenuItem } from '../ui'
import {
  ChevronDownIcon, ComposeIcon, CopyIcon, DownloadIcon, EditorIcon, FileIcon, MoreIcon, TrashIcon,
} from '../icons'

/**
 * The library as a table.
 *
 * A grid of cards is what you build when there are twelve documents and a
 * picture on each one. These have no picture, and there are eventually
 * hundreds — so the tool that people actually keep open all day shows them the
 * way Stripe and Linear show a list: fixed-height rows, one line each, the
 * columns aligned so the eye can run down a single one, and the numbers in
 * tabular figures so they do not wobble between rows.
 */
export function DocumentTable({
  documents,
  busyId,
  sort,
  onSort,
  onOpen,
  onExport,
  onDuplicate,
  onDelete,
}: {
  documents: DocumentItem[]
  busyId: { id: string; what: string } | null
  sort: SortKey
  onSort: (key: SortKey) => void
  onOpen: (doc: DocumentItem) => void
  onExport: (doc: DocumentItem, format: 'docx' | 'pdf') => void
  onDuplicate: (doc: DocumentItem) => void
  onDelete: (doc: DocumentItem) => void
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-surface">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">
          Your documents, sorted by {SORT_LABELS[sort].toLowerCase()}
        </caption>

        <thead>
          <tr className="border-b border-line">
            <Th className="w-auto">Name</Th>
            <Th className="hidden w-32 md:table-cell">Source</Th>
            <SortableTh
              className="hidden w-28 lg:table-cell"
              active={sort === 'versions'}
              onClick={() => onSort('versions')}
            >
              Versions
            </SortableTh>
            <SortableTh
              className="w-32"
              active={sort === 'newest' || sort === 'oldest'}
              descending={sort === 'newest'}
              onClick={() => onSort(sort === 'newest' ? 'oldest' : 'newest')}
            >
              Created
            </SortableTh>
            <th className="w-12 px-2" aria-label="Actions" />
          </tr>
        </thead>

        <tbody>
          {documents.map((doc) => {
            const busy = busyId?.id === doc.id ? busyId.what : null
            const generated = doc.source === 'generated'

            const menu: MenuItem[] = [
              {
                id: 'open',
                label: generated ? 'Open a copy in the editor' : 'Open in editor',
                icon: <EditorIcon />,
                onSelect: () => onOpen(doc),
              },
              { id: 'docx', label: 'Download DOCX', icon: <DownloadIcon />, onSelect: () => onExport(doc, 'docx') },
              { id: 'pdf', label: 'Download PDF', icon: <DownloadIcon />, onSelect: () => onExport(doc, 'pdf') },
              ...(generated
                ? []
                : [{ id: 'duplicate', label: 'Duplicate', icon: <CopyIcon />, onSelect: () => onDuplicate(doc) }]),
              {
                id: 'delete',
                label: generated ? 'Delete paper' : 'Delete document',
                icon: <TrashIcon />,
                destructive: true,
                onSelect: () => onDelete(doc),
              },
            ]

            return (
              <tr
                key={`${doc.source}:${doc.id}`}
                className={cn(
                  'group border-b border-line last:border-b-0 transition-colors duration-fast',
                  busy ? 'bg-surface-2/60' : 'hover:bg-surface-2/50',
                )}
              >
                <td className="max-w-0 px-3 py-0">
                  <button
                    type="button"
                    onClick={() => onOpen(doc)}
                    disabled={Boolean(busy)}
                    className="flex h-10 w-full items-center gap-2.5 text-left"
                  >
                    <span
                      className={cn('shrink-0', generated ? 'text-brand-ink' : 'text-faint')}
                      aria-hidden
                    >
                      {generated ? <ComposeIcon /> : <FileIcon />}
                    </span>
                    <span className="truncate text-sm font-medium text-ink group-hover:text-brand-ink">
                      {doc.title}
                    </span>
                    {busy && (
                      <span className="flex shrink-0 items-center gap-1.5 text-2xs text-muted">
                        <Spinner size="sm" />
                        {busy}
                      </span>
                    )}
                  </button>
                </td>

                {/* Text, not a badge: three identical pills down a column is
                    decoration, and the column header already says what it is. */}
                <td className="hidden px-3 text-sm text-muted md:table-cell">
                  <span className="flex items-center gap-1.5">
                    <span
                      className={cn('h-1.5 w-1.5 rounded-full', generated ? 'bg-brand' : 'bg-line-strong')}
                      aria-hidden
                    />
                    {generated ? doc.stylePreset || 'Generated' : 'Upload'}
                  </span>
                </td>

                <td className="hidden px-3 text-sm tabular-nums text-muted lg:table-cell">
                  {doc.versions ?? '—'}
                </td>

                <td className="px-3 text-sm tabular-nums text-muted">
                  {formatDate(doc.createdAt) || '—'}
                </td>

                <td className="px-2 text-right">
                  <Dropdown
                    label={`Actions for ${doc.title}`}
                    items={menu}
                    triggerVariant="ghost"
                    triggerSize="sm"
                    triggerIcon={<MoreIcon />}
                    disabled={Boolean(busy)}
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function Th({ className, children }: { className?: string; children?: React.ReactNode }) {
  return (
    <th
      scope="col"
      className={cn('px-3 py-2 text-2xs font-medium uppercase tracking-wide text-faint', className)}
    >
      {children}
    </th>
  )
}

/** A column header that sorts, and says which way it is sorting. */
function SortableTh({
  active, descending, onClick, className, children,
}: {
  active: boolean
  descending?: boolean
  onClick: () => void
  className?: string
  children: React.ReactNode
}) {
  return (
    <th
      scope="col"
      aria-sort={active ? (descending ? 'descending' : 'ascending') : 'none'}
      className={cn('px-3 py-2', className)}
    >
      <button
        type="button"
        onClick={onClick}
        className={cn(
          'flex items-center gap-1 rounded-sm text-2xs font-medium uppercase tracking-wide transition-colors duration-fast',
          active ? 'text-ink' : 'text-faint hover:text-muted',
        )}
      >
        {children}
        <ChevronDownIcon
          className={cn(
            'h-3 w-3 transition-transform duration-fast',
            !active && 'opacity-0 group-hover:opacity-100',
            active && !descending && 'rotate-180',
          )}
        />
      </button>
    </th>
  )
}

/** The table's shape while it loads: the same rows, without the words. */
export function DocumentTableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-surface" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex h-10 items-center gap-3 border-b border-line px-3 last:border-b-0">
          <div className="h-4 w-4 shrink-0 animate-pulse rounded-sm bg-surface-2" />
          <div className="h-3 flex-1 animate-pulse rounded-sm bg-surface-2" style={{ maxWidth: `${30 + ((i * 17) % 40)}%` }} />
          <div className="hidden h-4 w-16 animate-pulse rounded-sm bg-surface-2 md:block" />
          <div className="h-3 w-20 animate-pulse rounded-sm bg-surface-2" />
        </div>
      ))}
    </div>
  )
}
