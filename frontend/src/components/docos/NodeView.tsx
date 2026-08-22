import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { CSSProperties } from 'react'
import type { GraphNode, Style } from '../../types/docos'
import type { DiffMark } from '../../lib/diffMarks'
import { NODE_LABEL } from '../../lib/graphUtils'

function styleToCss(style: Style): CSSProperties {
  return {
    fontSize: style.font_size ? `${style.font_size}px` : undefined,
    fontWeight: style.bold ? 700 : undefined,
    fontStyle: style.italic ? 'italic' : undefined,
    textDecoration: style.underline ? 'underline' : undefined,
    color: style.color || undefined,
    backgroundColor: style.highlight || undefined,
    fontFamily: style.font_family || undefined,
    textAlign: (style.alignment as CSSProperties['textAlign']) || undefined,
  }
}

/** Line spacing and the gaps around a paragraph, as the document set them.
 *  Rendering a single-spaced document at 1.5 needs half again as much room as
 *  it has, which pushed text past the foot of the page. */
function spacingToCss(node: GraphNode): CSSProperties {
  const m = (node.metadata ?? {}) as Record<string, unknown>
  const out: CSSProperties = {}
  if (typeof m.line_spacing === 'number') {
    out.lineHeight = m.line_spacing_exact ? `${m.line_spacing}pt` : m.line_spacing
  }
  if (typeof m.space_before_pt === 'number') out.marginTop = `${m.space_before_pt}pt`
  if (typeof m.space_after_pt === 'number') out.marginBottom = `${m.space_after_pt}pt`
  return out
}

interface Props {
  node: GraphNode
  selected: boolean
  active: boolean
  removing: boolean
  /** Set while a compare result is open and names this node. */
  mark?: DiffMark
}

export function NodeView({ node, selected, active, removing, mark }: Props) {
  const css = { ...styleToCss(node.style), ...spacingToCss(node) }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{
        opacity: removing ? 0 : 1,
        x: removing ? 24 : 0,
        scale: active ? 1.01 : 1,
      }}
      exit={{ opacity: 0, x: 24 }}
      transition={{ duration: 0.22 }}
      className={clsx(
        'group relative rounded-lg px-3 py-1.5 transition-colors',
        selected && 'ring-2 ring-sky-400/70',
        active && 'bg-sky-400/10',
        mark && 'border-l-4 pl-2',
        mark?.kind === 'added' && 'border-emerald-500 bg-emerald-400/10',
        mark?.kind === 'changed' && 'border-amber-500 bg-amber-300/10',
      )}
    >
      {mark && (
        <span
          className={clsx(
            'pointer-events-none absolute -left-2 -top-1.5 -translate-x-full rounded px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wide text-white',
            mark.kind === 'added' ? 'bg-emerald-600' : 'bg-amber-600',
          )}
        >
          {mark.kind}
        </span>
      )}
      <span
        className="pointer-events-none absolute -left-1 top-1/2 -translate-x-full -translate-y-1/2 rounded bg-neutral-900/80 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-white opacity-0 transition-opacity group-hover:opacity-100 dark:bg-white/80 dark:text-neutral-900"
      >
        {NODE_LABEL[node.type]}
      </span>
      {renderBody(node, css, mark)}
    </motion.div>
  )
}

// The page is always a white sheet (see GraphCanvas), so text colours are fixed
// dark-on-white like Word — never inverted by the app's dark theme. Explicit
// colours parsed from the DOCX still win via inline `css`.
function renderBody(node: GraphNode, css: CSSProperties, mark?: DiffMark) {
  // The words themselves, marked up when a compare result knows how they changed.
  const text = <Text node={node} mark={mark} />
  switch (node.type) {
    case 'heading':
      return <h1 style={{ color: '#1a1a1a', ...css }} className="mb-1 mt-2 text-[20pt] font-semibold leading-snug">{node.content ? text : 'Heading'}</h1>
    case 'subheading':
      return <h2 style={{ color: '#2a2a2a', ...css }} className="mb-1 mt-1.5 text-[15pt] font-semibold leading-snug">{node.content ? text : 'Subheading'}</h2>
    case 'caption':
      return <div style={css} className="text-center text-[9pt] italic text-neutral-600">{text}</div>
    case 'reference':
      return <div style={css} className="pl-6 -indent-6 text-[10pt] leading-relaxed text-neutral-800">{text}</div>
    case 'footnote':
      return <div style={css} className="text-[9pt] text-neutral-500">{text}</div>
    case 'header':
    case 'footer':
      return <div style={css} className="text-[9pt] uppercase tracking-wide text-neutral-400">{node.type}: {text}</div>
    case 'horizontal_rule':
      return <hr className="my-2 border-neutral-400" />
    case 'page_break':
      return <div className="my-3 border-t-2 border-dashed border-neutral-300 text-center text-[8pt] uppercase tracking-widest text-neutral-400">page break</div>
    case 'figure':
      // A figure holds its pictures as children; render them, not a stand-in.
      return (
        <div className="my-2 space-y-2" style={{ backgroundColor: css.backgroundColor }}>
          {node.children.map((child) => (
            <ImageView key={child.id} node={child} css={styleToCss(child.style)} />
          ))}
        </div>
      )
    case 'image':
      return <ImageView node={node} css={css} />
    case 'table':
      return <TableView node={node} />
    default:
      return <p style={{ color: '#1a1a1a', ...css }} className="text-[11pt] leading-relaxed">{text}</p>
  }
}

/** A node's text: plain, or split into the words that left and the ones that
 *  arrived when a diff describes it. The page is a white sheet, so these keep
 *  fixed light-on-paper colours rather than theme tokens. */
function Text({ node, mark }: { node: GraphNode; mark?: DiffMark }) {
  if (!mark?.segments) return <>{node.content}</>
  return (
    <>
      {mark.segments.map((seg, i) =>
        seg.op === 'equal' ? (
          <span key={i}>{seg.text}</span>
        ) : seg.op === 'insert' ? (
          <ins key={i} className="rounded bg-emerald-200 text-emerald-900 no-underline">{seg.text}</ins>
        ) : (
          <del key={i} className="rounded bg-rose-200 text-rose-900">{seg.text}</del>
        ),
      )}
    </>
  )
}

/** The real picture when the importer could read it, and — when it could not —
 *  a placeholder that says which problem it hit, because "linked, not stored"
 *  and "too large" need different things from the reader. */
function ImageView({ node, css }: { node: GraphNode; css: React.CSSProperties }) {
  const meta = (node.metadata ?? {}) as Record<string, unknown>
  const src = typeof meta.src === 'string' ? meta.src : ''
  const linkedTo = typeof meta.linked_to === 'string' ? meta.linked_to : ''
  const tooLarge = typeof meta.too_large === 'number'

  const reason = linkedTo
    ? 'Linked to a file outside this document, so the picture was not stored in it. Re-insert it in Word with Insert › Picture (not Link to File) and import again.'
    : tooLarge
      ? 'Too large to preview. It is still part of the document.'
      : 'This picture could not be read from the file.'

  if (src) {
    return (
      <figure className="my-1" style={{ textAlign: css.textAlign }}>
        <img
          src={src}
          alt={node.content || 'Figure'}
          className="inline-block h-auto max-w-full rounded"
        />
        {node.content && (
          <figcaption className="mt-1 text-[9pt] text-neutral-600">{node.content}</figcaption>
        )}
      </figure>
    )
  }

  return (
    <div className="my-1 flex items-start gap-3 rounded border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4">
      <span className="text-2xl leading-none">🖼️</span>
      <span className="min-w-0">
        <span className="block text-[10pt] text-neutral-700">{node.content || 'Figure'}</span>
        <span className="mt-0.5 block text-[9pt] leading-relaxed text-neutral-500">{reason}</span>
        {linkedTo && (
          <span className="mt-0.5 block truncate font-mono text-[8pt] text-neutral-400">
            {linkedTo}
          </span>
        )}
      </span>
    </div>
  )
}

function TableView({ node }: { node: GraphNode }) {
  return (
    <div className="my-1 overflow-x-auto">
      <table className="w-full border-collapse text-[10pt]">
        <tbody>
          {node.children.map((row) => (
            <tr key={row.id}>
              {row.children.map((cell) => (
                <td key={cell.id} className="border border-neutral-400 px-3 py-1.5 align-top text-neutral-900">
                  {cell.content}
                  {/* a screenshot laid out in a table is still a picture */}
                  {cell.children.map((pic) => (
                    <ImageView key={pic.id} node={pic} css={styleToCss(pic.style)} />
                  ))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
