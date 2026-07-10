import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { CSSProperties } from 'react'
import type { GraphNode, Style } from '../../types/docos'
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

interface Props {
  node: GraphNode
  selected: boolean
  active: boolean
  removing: boolean
}

export function NodeView({ node, selected, active, removing }: Props) {
  const css = styleToCss(node.style)

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
      )}
    >
      <span
        className="pointer-events-none absolute -left-1 top-1/2 -translate-x-full -translate-y-1/2 rounded bg-neutral-900/80 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-white opacity-0 transition-opacity group-hover:opacity-100 dark:bg-white/80 dark:text-neutral-900"
      >
        {NODE_LABEL[node.type]}
      </span>
      {renderBody(node, css)}
    </motion.div>
  )
}

function renderBody(node: GraphNode, css: CSSProperties) {
  switch (node.type) {
    case 'heading':
      return <div style={css} className="text-2xl font-semibold text-neutral-900 dark:text-neutral-50">{node.content || 'Heading'}</div>
    case 'subheading':
      return <div style={css} className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">{node.content || 'Subheading'}</div>
    case 'caption':
      return <div style={css} className="text-center text-xs italic text-neutral-600 dark:text-neutral-400">{node.content}</div>
    case 'reference':
      return <div style={css} className="pl-6 -indent-6 text-sm text-neutral-700 dark:text-neutral-300">{node.content}</div>
    case 'footnote':
      return <div style={css} className="text-xs text-neutral-500 dark:text-neutral-400">{node.content}</div>
    case 'header':
    case 'footer':
      return <div style={css} className="text-xs uppercase tracking-wide text-neutral-400">{node.type}: {node.content}</div>
    case 'horizontal_rule':
      return <hr className="my-2 border-neutral-300 dark:border-neutral-700" />
    case 'page_break':
      return <div className="my-3 border-t-2 border-dashed border-neutral-300 text-center text-[10px] uppercase tracking-widest text-neutral-400 dark:border-neutral-700">page break</div>
    case 'figure':
    case 'image':
      return (
        <div className="flex items-center gap-3 rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-4 py-6 dark:border-neutral-700 dark:bg-neutral-900/40" style={{ backgroundColor: css.backgroundColor }}>
          <span className="text-2xl">🖼️</span>
          <span className="text-sm text-neutral-600 dark:text-neutral-300">{node.content || 'Figure'}</span>
        </div>
      )
    case 'table':
      return <TableView node={node} />
    default:
      return <p style={css} className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">{node.content}</p>
  }
}

function TableView({ node }: { node: GraphNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <tbody>
          {node.children.map((row) => (
            <tr key={row.id}>
              {row.children.map((cell) => (
                <td key={cell.id} className="border border-neutral-300 px-3 py-1.5 text-neutral-800 dark:border-neutral-700 dark:text-neutral-200">
                  {cell.content}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
