import type { DocumentGraph, GraphNode, NodeType, Style } from '../types/docos'

/** Flatten the graph into document-order nodes (excluding the document root). */
export function flatten(graph: DocumentGraph | null): GraphNode[] {
  if (!graph) return []
  const out: GraphNode[] = []
  const walk = (n: GraphNode, isRoot: boolean) => {
    if (!isRoot) out.push(n)
    n.children?.forEach((c) => walk(c, false))
  }
  walk(graph.root, true)
  return out
}

/** Return a new graph with `fn` applied to the node matching `id`. */
export function updateNode(
  graph: DocumentGraph,
  id: string,
  fn: (n: GraphNode) => GraphNode,
): DocumentGraph {
  const map = (n: GraphNode): GraphNode => {
    const next = n.id === id ? fn(n) : n
    if (!next.children?.length) return next
    return { ...next, children: next.children.map(map) }
  }
  return { ...graph, root: map(graph.root) }
}

/** Return a new graph with the node matching `id` removed. */
export function removeNode(graph: DocumentGraph, id: string): DocumentGraph {
  const prune = (n: GraphNode): GraphNode => ({
    ...n,
    children: (n.children || []).filter((c) => c.id !== id).map(prune),
  })
  return { ...graph, root: prune(graph.root) }
}

export function patchStyle(node: GraphNode, patch: Partial<Style>): GraphNode {
  return { ...node, style: { ...node.style, ...patch } }
}

export const NODE_LABEL: Record<NodeType, string> = {
  document: 'Document', paragraph: 'Paragraph', heading: 'Heading',
  subheading: 'Subheading', body: 'Body', image: 'Image', figure: 'Figure',
  caption: 'Caption', table: 'Table', table_row: 'Row', table_cell: 'Cell',
  horizontal_rule: 'Rule', page_break: 'Page break', header: 'Header',
  footer: 'Footer', reference: 'Reference', footnote: 'Footnote',
}
