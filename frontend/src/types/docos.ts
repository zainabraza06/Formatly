// Types mirroring the DocOS backend (app/docos).

export type NodeType =
  | 'document' | 'paragraph' | 'heading' | 'subheading' | 'body'
  | 'image' | 'figure' | 'caption' | 'table' | 'table_row' | 'table_cell'
  | 'horizontal_rule' | 'page_break' | 'header' | 'footer' | 'reference' | 'footnote'

export interface Style {
  font_family?: string | null
  font_size?: number | null
  bold?: boolean | null
  italic?: boolean | null
  underline?: boolean | null
  color?: string | null
  highlight?: string | null
  alignment?: 'left' | 'center' | 'right' | 'justify' | null
}

export interface GraphNode {
  id: string
  type: NodeType
  content: string
  style: Style
  metadata: Record<string, unknown>
  children: GraphNode[]
}

export interface DocumentGraph {
  root: GraphNode
  title: string
}

export interface VersionInfo {
  id: string
  parent_id: string | null
  seq: number
  timestamp: string
  user: string
  label: string
  is_checkpoint: boolean
  is_current: boolean
}

export interface ImportResponse {
  document_id: string
  title: string
  version: VersionInfo
  graph: DocumentGraph
}

export interface GetDocumentResponse {
  document_id: string
  title: string
  current_version: string | null
  graph: DocumentGraph
}

// ── streamed events ─────────────────────────────────────────────────────────
export type DocOSEventName =
  | 'command_parsed' | 'batch_started' | 'batch_finished' | 'batch_failed'
  | 'selection_started' | 'selection_item' | 'selection_finished'
  | 'format_started' | 'format_progress' | 'format_finished'
  | 'delete_started' | 'delete_item' | 'delete_finished'
  | 'insert_started' | 'insert_item' | 'insert_finished'
  | 'move_started' | 'move_item' | 'move_finished'
  | 'replace_started' | 'replace_item' | 'replace_finished'
  | 'action_error' | 'version_committed' | 'version_changed'
  | 'control_noop' | 'compare_result' | 'error'

export interface DocOSEvent {
  event: DocOSEventName
  payload: Record<string, any>
}

export interface GraphDiff {
  added: Array<{ id: string; type: string; content: string }>
  removed: Array<{ id: string; type: string; content: string }>
  changed: Array<{ id: string; type: string; content?: any; style?: any }>
}
