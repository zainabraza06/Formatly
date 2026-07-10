import { useCallback, useEffect, useRef, useState } from 'react'
import { docosApi } from '../lib/docosApi'
import { patchStyle, removeNode, updateNode } from '../lib/graphUtils'
import type {
  DocOSEvent,
  DocumentGraph,
  GraphDiff,
  VersionInfo,
} from '../types/docos'

export interface PanelState {
  task: string
  reasoning: string
  provider: string
  source: string
  currentAction: string
  progress: { done: number; total: number } | null
  history: string[]
  upcoming: string[]
  error: string | null
}

const EMPTY_PANEL: PanelState = {
  task: '', reasoning: '', provider: '', source: '',
  currentAction: 'Idle', progress: null, history: [], upcoming: [], error: null,
}

// pacing (ms) so operations animate one-by-one rather than instantly
const ITEM_DELAY = 220
const STEP_DELAY = 70

export function useDocOS() {
  const [docId, setDocId] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [graph, setGraph] = useState<DocumentGraph | null>(null)
  const [status, setStatus] = useState<'idle' | 'ready' | 'running'>('idle')
  const [connected, setConnected] = useState(false)

  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [removingIds, setRemovingIds] = useState<string[]>([])
  const [panel, setPanel] = useState<PanelState>(EMPTY_PANEL)
  const [versions, setVersions] = useState<VersionInfo[]>([])
  const [diff, setDiff] = useState<{ a: number; b: number; diff: GraphDiff } | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const queueRef = useRef<DocOSEvent[]>([])
  const drainingRef = useRef(false)
  const docIdRef = useRef<string | null>(null)

  // ── event queue (paced) ───────────────────────────────────────────────────
  const enqueue = useCallback((ev: DocOSEvent) => {
    queueRef.current.push(ev)
    if (!drainingRef.current) void drain()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const drain = useCallback(async () => {
    drainingRef.current = true
    while (queueRef.current.length) {
      const ev = queueRef.current.shift()!
      const delay = handleEvent(ev)
      // eslint-disable-next-line no-await-in-loop
      await sleep(delay)
    }
    drainingRef.current = false
  }, [])

  const handleEvent = useCallback((ev: DocOSEvent): number => {
    const p = ev.payload || {}
    switch (ev.event) {
      case 'command_parsed': {
        const actions: any[] = p.actions || []
        setPanel((s) => ({
          ...s,
          reasoning: p.reasoning || '',
          provider: p.provider || '',
          source: p.source || '',
          upcoming: actions.map((a) => `${a.type}${a.target ? ` · ${a.target}` : ''}`),
          error: null,
        }))
        return STEP_DELAY
      }
      case 'batch_started':
        setStatus('running')
        setPanel((s) => ({ ...s, currentAction: 'Scanning document…', progress: null }))
        return STEP_DELAY

      case 'selection_started':
        setSelectedIds([])
        setPanel((s) => ({
          ...s,
          currentAction: `Selecting ${p.target ?? 'nodes'}… found ${p.total}`,
          progress: { done: 0, total: p.total ?? 0 },
        }))
        return STEP_DELAY
      case 'selection_item':
        setActiveId(p.id)
        setSelectedIds((ids) => (ids.includes(p.id) ? ids : [...ids, p.id]))
        setPanel((s) => ({ ...s, progress: s.progress ? { ...s.progress, done: s.progress.done + 1 } : null }))
        return ITEM_DELAY
      case 'selection_finished':
        setActiveId(null)
        setPanel((s) => ({ ...s, currentAction: `Selected ${(p.ids || []).length} node(s)` }))
        return STEP_DELAY

      case 'format_started':
        setPanel((s) => ({
          ...s,
          currentAction: `Formatting ${p.target ?? ''}…`.trim(),
          progress: { done: 0, total: p.total ?? 0 },
        }))
        return STEP_DELAY
      case 'format_progress':
        setActiveId(p.id)
        setGraph((g) => (g && p.id && p.style ? updateNode(g, p.id, (n) => ({ ...n, style: p.style })) : g))
        if (p.highlight) setGraph((g) => (g && p.id ? updateNode(g, p.id, (n) => patchStyle(n, { highlight: p.highlight })) : g))
        setPanel((s) => ({ ...s, progress: s.progress ? { ...s.progress, done: s.progress.done + 1 } : null }))
        return ITEM_DELAY
      case 'format_finished':
        setActiveId(null)
        setPanel((s) => ({ ...s, currentAction: `Formatted ${p.count} node(s)` }))
        return STEP_DELAY

      case 'delete_started':
        setPanel((s) => ({ ...s, currentAction: `Deleting ${p.target ?? ''}…`.trim(), progress: { done: 0, total: p.total ?? 0 } }))
        return STEP_DELAY
      case 'delete_item':
        setActiveId(p.id)
        setRemovingIds((ids) => [...ids, p.id])
        setPanel((s) => ({ ...s, progress: s.progress ? { ...s.progress, done: s.progress.done + 1 } : null }))
        // remove from graph after the fade-out
        window.setTimeout(() => {
          setGraph((g) => (g && p.id ? removeNode(g, p.id) : g))
          setRemovingIds((ids) => ids.filter((x) => x !== p.id))
        }, ITEM_DELAY)
        return ITEM_DELAY
      case 'delete_finished':
        setActiveId(null)
        setPanel((s) => ({ ...s, currentAction: `Deleted ${p.count} node(s)` }))
        return STEP_DELAY

      case 'replace_item':
      case 'insert_item':
      case 'move_item':
        setActiveId(p.id)
        return ITEM_DELAY

      case 'batch_failed':
        setPanel((s) => ({ ...s, error: `Action ${p.index} failed: ${p.error}`, currentAction: 'Rolled back' }))
        return STEP_DELAY
      case 'action_error':
        setPanel((s) => ({ ...s, error: p.detail || p.error || 'error' }))
        return STEP_DELAY

      case 'batch_finished':
      case 'version_committed':
      case 'version_changed':
        // sync authoritative graph + history once the animation settles
        void syncAfterCommit()
        setPanel((s) => ({ ...s, currentAction: 'Done', upcoming: [] }))
        return STEP_DELAY

      case 'compare_result':
        setDiff({ a: p.a, b: p.b, diff: p.diff })
        return STEP_DELAY
      case 'control_noop':
        setPanel((s) => ({ ...s, currentAction: `Nothing to ${p.op}` }))
        return STEP_DELAY
      case 'error':
        setPanel((s) => ({ ...s, error: p.detail || 'error' }))
        return STEP_DELAY
      default:
        return STEP_DELAY
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const syncAfterCommit = useCallback(async () => {
    const id = docIdRef.current
    if (!id) return
    try {
      const [doc, hist] = await Promise.all([docosApi.getDocument(id), docosApi.history(id)])
      setGraph(doc.graph)
      setVersions(hist)
      setStatus('ready')
      setPanel((s) => ({ ...s, history: [s.currentAction, ...s.history].filter(Boolean).slice(0, 20) }))
    } catch {
      setStatus('ready')
    }
  }, [])

  // ── websocket lifecycle ────────────────────────────────────────────────────
  const openSocket = useCallback((id: string) => {
    wsRef.current?.close()
    const ws = new WebSocket(docosApi.wsUrl(id))
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      try {
        enqueue(JSON.parse(e.data) as DocOSEvent)
      } catch { /* ignore malformed */ }
    }
    wsRef.current = ws
  }, [enqueue])

  useEffect(() => () => wsRef.current?.close(), [])

  const bindDoc = useCallback((id: string, g: DocumentGraph, t: string) => {
    docIdRef.current = id
    setDocId(id)
    setGraph(g)
    setTitle(t)
    setSelectedIds([])
    setDiff(null)
    setPanel(EMPTY_PANEL)
    setStatus('ready')
    openSocket(id)
    docosApi.history(id).then(setVersions).catch(() => {})
  }, [openSocket])

  // ── public actions ─────────────────────────────────────────────────────────
  const importFile = useCallback(async (file: File) => {
    setStatus('running')
    const res = await docosApi.importDocx(file)
    bindDoc(res.document_id, res.graph, res.title)
    return res
  }, [bindDoc])

  const loadDocument = useCallback(async (id: string) => {
    const doc = await docosApi.getDocument(id)
    bindDoc(id, doc.graph, doc.title)
  }, [bindDoc])

  const runCommand = useCallback((command: string) => {
    if (!docId) return
    setPanel((s) => ({ ...EMPTY_PANEL, task: command, history: s.history }))
    setDiff(null)
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ command }))
    } else {
      // REST fallback: replay collected events through the same paced queue
      docosApi.command(docId, command).then((r) => {
        ;(r.events || []).forEach((ev) => enqueue(ev as DocOSEvent))
      })
    }
  }, [docId, enqueue])

  const undo = useCallback(() => runCommand('Undo'), [runCommand])
  const redo = useCallback(() => runCommand('Redo'), [runCommand])
  const rewind = useCallback((seq: number) => runCommand(`Rewind to version ${seq}`), [runCommand])
  const restore = useCallback((seq: number) => runCommand(`Restore version ${seq}`), [runCommand])
  const compare = useCallback((a: number, b: number) => runCommand(`Compare version ${a} and ${b}`), [runCommand])

  return {
    docId, title, graph, status, connected,
    selectedIds, activeId, removingIds, panel, versions, diff,
    importFile, loadDocument, runCommand, undo, redo, rewind, restore, compare,
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
