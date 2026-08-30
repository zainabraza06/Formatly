import { useCallback, useEffect, useRef, useState } from 'react'
import { docosApi } from '../lib/docosApi'
import { patchStyle, removeNode, updateNode } from '../lib/graphUtils'
import type {
  DocOSEvent,
  DocumentGraph,
  GraphDiff,
  VersionInfo,
} from '../types/docos'

/** One prompt the user gave while formatting, and what came of it. */
export interface HistoryEntry {
  prompt: string
  outcome: string
}

export interface PanelState {
  task: string
  reasoning: string
  provider: string
  source: string
  currentAction: string
  progress: { done: number; total: number } | null
  history: HistoryEntry[]
  upcoming: string[]
  error: string | null
  /** The assistant reading the document through, which happens on import and
   *  runs alongside anything else. Its own line, so it cannot overwrite a
   *  command's progress. */
  reading: { page: number; of: number } | null
}

const EMPTY_PANEL: PanelState = {
  task: '', reasoning: '', provider: '', source: '',
  currentAction: 'Idle', progress: null, history: [], upcoming: [], error: null,
  reading: null,
}

// pacing (ms) so operations animate one-by-one rather than instantly
const ITEM_DELAY = 220
const STEP_DELAY = 70

export function useDocOS() {
  const [docId, setDocId] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [graph, setGraph] = useState<DocumentGraph | null>(null)
  const [status, setStatus] = useState<'idle' | 'ready' | 'running'>('idle')
  // Read inside the event handler, which is created once and would otherwise
  // close over the first render's status forever.
  const statusRef = useRef(status)
  useEffect(() => {
    statusRef.current = status
  }, [status])
  // The same, for the graph: the event handler is created once, and needs to
  // know what the document currently is without being rebuilt for every edit.
  const graphRef = useRef(graph)
  useEffect(() => {
    graphRef.current = graph
  }, [graph])
  const [connected, setConnected] = useState(false)

  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  // The node the editor should turn to — set while the assistant is reading
  // through a document, so the page on screen is the page being worked on.
  const [focusId, setFocusId] = useState<string | null>(null)
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
          // A plan made without the planner is worth saying so, with the reason.
          // "via heuristic" on its own looks like a choice rather than a failure.
          error: p.fell_back_because
            ? `The planner could not be used (${p.fell_back_because}); this plan is a fallback.`
            : null,
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

      case 'reading_started':
        setPanel((s) => ({ ...s, reading: { page: 0, of: 0 } }))
        return STEP_DELAY
      case 'reading_progress': {
        // The assistant reads a long document a page at a time. It has its own
        // line in the panel because it runs on its own schedule: writing it
        // into the line a command uses meant a reading that finished mid-command
        // replaced "Deleting…" with "Idle", and the command looked dead.
        const ids: string[] = Array.isArray(p.ids) ? p.ids : []
        // Only follow the reading around the document when nothing else is
        // using the page; a command's own focus outranks it.
        if (ids.length && statusRef.current !== 'running') setFocusId(ids[0])
        setPanel((s) => ({ ...s, reading: { page: p.page ?? 0, of: p.of ?? 0 } }))
        return STEP_DELAY
      }
      case 'reading_finished':
        // Put the reader back where they started. Following the assistant
        // through the document is the point of the sweep, but leaving someone
        // on page five of a report they have not read a word of is not.
        if (statusRef.current !== 'running') {
          const first = graphRef.current?.root?.children?.[0]?.id
          setFocusId(first ?? null)
        }
        setPanel((s) => ({ ...s, reading: null }))
        return STEP_DELAY

      case 'section_located':
        // Say which part of the document an instruction was taken to mean, so a
        // wrong guess is visible rather than mysterious.
        setPanel((s) => ({ ...s, currentAction: `Working on “${p.heading}”` }))
        return STEP_DELAY

      case 'rewrite_progress': {
        // The assistant reads a long document a page at a time. Following it
        // there turns "nothing seems to be happening" into visible progress.
        const ids: string[] = Array.isArray(p.ids) ? p.ids : []
        if (ids.length) {
          setFocusId(ids[0])
          setSelectedIds(ids)
        }
        setPanel((s) => ({
          ...s,
          // "Reading" here read as though the document were being read again,
          // which is a different thing that also says so on its own line.
          currentAction: `Rewriting — part ${p.pass ?? '?'} of ${p.of ?? '?'}…`,
          progress: { done: (p.pass ?? 1) - 1, total: p.of ?? 0 },
        }))
        return STEP_DELAY
      }
      case 'rewrite_finished':
        setSelectedIds([])
        setPanel((s) => ({
          ...s,
          currentAction: `Rewrote ${p.edited ?? 0} passage(s)`,
          // A pass that never came back is worth saying out loud rather than
          // leaving the reader to notice the gap themselves.
          error: (p.warnings || []).length
            ? `${(p.warnings || []).length} passage(s) could not be rewritten: ${(p.warnings || [])[0]}`
            : s.error,
        }))
        return STEP_DELAY

      case 'batch_failed':
        setPanel((s) => ({ ...s, error: `Action ${p.index} failed: ${p.error}`, currentAction: 'Rolled back' }))
        return STEP_DELAY
      case 'action_error':
        setPanel((s) => ({ ...s, error: p.detail || p.error || 'error' }))
        return STEP_DELAY

      case 'command_noop':
        // Nothing matched, so nothing changed. Saying "Done" here is how an
        // instruction that did nothing came to look like it had worked.
        setPanel((s) => ({
          ...s,
          currentAction: 'Nothing changed',
          error: p.reason || 'nothing matched, so nothing changed',
        }))
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
      // Record the prompt and its outcome. Several events (batch_finished,
      // version_committed) sync, so update the current prompt's entry in place
      // rather than logging it repeatedly.
      setPanel((s) => {
        if (!s.task) return s
        const rest = s.history[0]?.prompt === s.task ? s.history.slice(1) : s.history
        return { ...s, history: [{ prompt: s.task, outcome: s.currentAction }, ...rest].slice(0, 20) }
      })
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
    // Say so immediately. The first event cannot arrive until the planner has
    // answered, and a planner can take a minute or time out — during which the
    // panel used to read "Idle", so a command that was working looked dead.
    setPanel((s) => ({
      ...EMPTY_PANEL, task: command, currentAction: 'Planning…', history: s.history,
    }))
    setStatus('running')
    setDiff(null)

    const failed = (detail: string) => {
      setStatus('ready')
      setPanel((s) => ({ ...s, currentAction: 'Could not run', error: detail }))
    }

    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ command }))
      } catch (e) {
        failed(e instanceof Error ? e.message : 'the connection dropped')
      }
    } else {
      // REST fallback: replay collected events through the same paced queue
      docosApi.command(docId, command)
        .then((r) => { (r.events || []).forEach((ev) => enqueue(ev as DocOSEvent)) })
        // Without this a failed request left the panel saying "Planning…" for ever.
        .catch((e) => failed(e instanceof Error ? e.message : 'the request failed'))
    }
  }, [docId, enqueue])

  const undo = useCallback(() => runCommand('Undo'), [runCommand])
  const redo = useCallback(() => runCommand('Redo'), [runCommand])
  const rewind = useCallback((seq: number) => runCommand(`Rewind to version ${seq}`), [runCommand])
  const restore = useCallback((seq: number) => runCommand(`Restore version ${seq}`), [runCommand])
  const compare = useCallback((a: number, b: number) => runCommand(`Compare version ${a} and ${b}`), [runCommand])
  const clearDiff = useCallback(() => setDiff(null), [])

  return {
    docId, title, graph, status, connected,
    selectedIds, activeId, focusId, removingIds, panel, versions, diff,
    importFile, loadDocument, runCommand, undo, redo, rewind, restore, compare, clearDiff,
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
