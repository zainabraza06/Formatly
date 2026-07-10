import { AnimatePresence } from 'framer-motion'
import { flatten } from '../../lib/graphUtils'
import type { DocumentGraph } from '../../types/docos'
import { NodeView } from './NodeView'

interface Props {
  graph: DocumentGraph | null
  selectedIds: string[]
  activeId: string | null
  removingIds: string[]
}

export function GraphCanvas({ graph, selectedIds, activeId, removingIds }: Props) {
  const nodes = flatten(graph)
  const selected = new Set(selectedIds)
  const removing = new Set(removingIds)

  if (!graph) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-neutral-500">
        Import a DOCX to begin.
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-1 rounded-2xl bg-white px-8 py-10 shadow-sm dark:bg-neutral-950/60">
      <AnimatePresence initial={false}>
        {nodes.map((n) => (
          <NodeView
            key={n.id}
            node={n}
            selected={selected.has(n.id)}
            active={activeId === n.id}
            removing={removing.has(n.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}
