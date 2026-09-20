import { useCallback, useEffect, useRef, useState } from 'react'
import { docosApi } from '../lib/docosApi'
import { explain } from '../lib/errors'
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
  /** What was done, in the document's terms — not the planner's note to
   *  itself, which talks about node ids and describes an intention rather
   *  than an outcome. */
  summary: string
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

/** An assistant edit that has landed but has not been looked at yet. */
export interface ReviewState {
  /** The instruction that caused it, in the reader's own words. */
  command: string
  /** What the assistant says it did. */
  summary: string
  /** The versions either side of the change, for the diff. */
  before: number
  after: number
}

const EMPTY_PANEL: PanelState = {
  task: '', summary: '', provider: '', source: '',
  currentAction: 'Idle', progress: null, history: [], upcoming: [], error: null,
  reading: null,
}

/** Timeline controls are not edits to review — they are the review. */
const UNTRACKED = { track: false } as const

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
  /** live: the socket is open. connecting: it dropped and is being retried.
   *  offline: no socket — commands still run over REST, just without the
   *  step-by-step commentary. */
  const [connection, setConnection] = useState<'live' | 'connecting' | 'offline'>('offline')
  /** A document is being fetched or imported. Without this the editor cannot
   *  tell "nothing is open" from "what you asked for is on its way", and shows
   *  the empty state either way — which reads as a link that did nothing. */
  const [opening, setOpening] = useState(false)

  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  // The node the editor should turn to — set while the assistant is reading
  // through a document, so the page on screen is the page being worked on.
  const [focusId, setFocusId] = useState<string | null>(null)
  const [removingIds, setRemovingIds] = useState<string[]>([])
  const [panel, setPanel] = useState<PanelState>(EMPTY_PANEL)
  const [versions, setVersions] = useState<VersionInfo[]>([])
  const [diff, setDiff] = useState<{ a: number; b: number; diff: GraphDiff } | null>(null)
  /** The last thing the assistant did to the document, waiting to be kept or
   *  undone. Every AI edit passes through here, so none of them is final until
   *  the reader has seen it. */
  const [review, setReview] = useState<ReviewState | null>(null)

  // The version the document was on when the current command started, so the
  // review can name both ends of what changed.
  const beforeRef = useRef<number | null>(null)
  const trackingRef = useRef<string | null>(null)

  // The version list as it is right now, for the same reason: runCommand is
  // rebuilt only when the document changes, not on every commit.
  const versionsRef = useRef<VersionInfo[]>([])
  useEffect(() => {
    versionsRef.current = versions
  }, [versions])

  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<number | null>(null)
  const attemptsRef = useRef(0)
  /** Set while the socket is being replaced on purpose, so the close handler
   *  does not treat it as a drop and start reconnecting to a closed document. */
  const closingRef = useRef(false)
  const queueRef = useRef<DocOSEvent[]>([])
  const drainingRef = useRef(false)
  const docIdRef = useRef<string | null>(null)

  // ── event queue (paced) ───────────────────────────────────────────────────
  // Defined in the order they call each other — sync, then the handler that
  // triggers it, then the drain that runs the handler, then the enqueue that
  // starts the drain — so none of them refers to a binding declared below it.
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
        // An edit the reader has not seen yet is not finished. Offering it for
        // review is what makes an AI change reversible in one click rather
        // than something to go hunting for in the timeline afterwards.
        const command = trackingRef.current
        const before = beforeRef.current
        const after = hist.find((v) => v.is_current)?.seq ?? null
        if (command && before !== null && after !== null && after !== before) {
          setReview({ command, summary: s.summary || s.currentAction, before, after })
          trackingRef.current = null
          beforeRef.current = null
        }
        return { ...s, history: [{ prompt: s.task, outcome: s.currentAction }, ...rest].slice(0, 20) }
      })
    } catch {
      setStatus('ready')
    }
  }, [])

  const handleEvent = useCallback((ev: DocOSEvent): number => {
    const p = ev.payload || {}
    switch (ev.event) {
      case 'command_parsed': {
        const actions = p.actions ?? []
        setPanel((s) => ({
          ...s,
          summary: '',
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
        setActiveId(p.id ?? null)
        if (p.id) {
          const id = p.id
          setSelectedIds((ids) => (ids.includes(id) ? ids : [...ids, id]))
        }
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
      case 'format_progress': {
        setActiveId(p.id ?? null)
        const { id, style, highlight } = p
        if (id && style) setGraph((g) => (g ? updateNode(g, id, (n) => ({ ...n, style })) : g))
        if (id && highlight) {
          setGraph((g) => (g ? updateNode(g, id, (n) => patchStyle(n, { highlight })) : g))
        }
        setPanel((s) => ({ ...s, progress: s.progress ? { ...s.progress, done: s.progress.done + 1 } : null }))
        return ITEM_DELAY
      }
      case 'format_finished':
        setActiveId(null)
        setPanel((s) => ({ ...s, currentAction: `Formatted ${p.count} node(s)` }))
        return STEP_DELAY

      case 'delete_started':
        setPanel((s) => ({ ...s, currentAction: `Deleting ${p.target ?? ''}…`.trim(), progress: { done: 0, total: p.total ?? 0 } }))
        return STEP_DELAY
      case 'delete_item': {
        setActiveId(p.id ?? null)
        const removing = p.id
        if (removing) setRemovingIds((ids) => [...ids, removing])
        setPanel((s) => ({ ...s, progress: s.progress ? { ...s.progress, done: s.progress.done + 1 } : null }))
        // remove from graph after the fade-out
        window.setTimeout(() => {
          setGraph((g) => (g && removing ? removeNode(g, removing) : g))
          setRemovingIds((ids) => ids.filter((x) => x !== removing))
        }, ITEM_DELAY)
        return ITEM_DELAY
      }
      case 'delete_finished':
        setActiveId(null)
        setPanel((s) => ({ ...s, currentAction: `Deleted ${p.count} node(s)` }))
        return STEP_DELAY

      case 'replace_item':
      case 'insert_item':
      case 'move_item':
        setActiveId(p.id ?? null)
        return ITEM_DELAY

      case 'reading_started':
        setPanel((s) => ({ ...s, reading: { page: 0, of: 0 } }))
        return STEP_DELAY
      case 'reading_progress': {
        // The assistant reads a long document a page at a time. It has its own
        // line in the panel because it runs on its own schedule: writing it
        // into the line a command uses meant a reading that finished mid-command
        // replaced "Deleting…" with "Idle", and the command looked dead.
        const ids = p.ids ?? []
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
        const ids = p.ids ?? []
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
        setPanel((s) => ({ ...s, currentAction: 'Done', upcoming: [],
                           summary: p.summary || s.summary }))
        return STEP_DELAY

      case 'compare_result':
        // Sent together or not at all; a partial compare result is not one.
        if (p.a !== undefined && p.b !== undefined && p.diff) {
          setDiff({ a: p.a, b: p.b, diff: p.diff })
        }
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

  const drain = useCallback(async () => {
    drainingRef.current = true
    while (queueRef.current.length) {
      const ev = queueRef.current.shift()!
      const delay = handleEvent(ev)
      // Deliberately serial: the pacing is the point. Each event is shown,
      // then the next one.
      await sleep(delay)
    }
    drainingRef.current = false
  }, [handleEvent])

  const enqueue = useCallback((ev: DocOSEvent) => {
    queueRef.current.push(ev)
    if (!drainingRef.current) void drain()
  }, [drain])

  // ── websocket lifecycle ────────────────────────────────────────────────────
  // The socket opener, reachable from its own close handler without the
  // callback referring to itself while it is still being defined.
  const openRef = useRef<((id: string) => void) | null>(null)

  const openSocket = useCallback((id: string) => {
    closingRef.current = true
    wsRef.current?.close()
    closingRef.current = false
    if (retryRef.current) window.clearTimeout(retryRef.current)

    setConnection('connecting')
    const ws = new WebSocket(docosApi.wsUrl(id))

    ws.onopen = () => {
      attemptsRef.current = 0
      setConnection('live')
    }

    ws.onclose = () => {
      if (closingRef.current || docIdRef.current !== id) return
      // A dropped socket used to stay dropped: the dot went grey and the
      // commentary never came back, while commands quietly fell through to
      // REST. Retry, backing off, and say which of the two is happening.
      setConnection('connecting')
      const wait = Math.min(1000 * 2 ** attemptsRef.current, 10_000)
      attemptsRef.current += 1
      retryRef.current = window.setTimeout(() => {
        if (docIdRef.current === id) openRef.current?.(id)
      }, wait)
    }

    ws.onerror = () => {
      // onclose follows, which is where the retry lives.
    }

    ws.onmessage = (e) => {
      try {
        enqueue(JSON.parse(e.data) as DocOSEvent)
      } catch { /* ignore malformed */ }
    }

    wsRef.current = ws
  }, [enqueue])

  useEffect(() => {
    openRef.current = openSocket
  }, [openSocket])

  useEffect(() => () => {
    closingRef.current = true
    if (retryRef.current) window.clearTimeout(retryRef.current)
    wsRef.current?.close()
  }, [])

  const bindDoc = useCallback((id: string, g: DocumentGraph, t: string) => {
    docIdRef.current = id
    setDocId(id)
    setGraph(g)
    setTitle(t)
    setSelectedIds([])
    setDiff(null)
    setPanel(EMPTY_PANEL)
    setReview(null)
    setStatus('ready')
    openSocket(id)
    docosApi.history(id).then(setVersions).catch(() => {})
  }, [openSocket])

  // ── public actions ─────────────────────────────────────────────────────────
  const importFile = useCallback(async (file: File) => {
    setOpening(true)
    setStatus('running')
    try {
      const res = await docosApi.importDocx(file)
      bindDoc(res.document_id, res.graph, res.title)
      return res
    } finally {
      setOpening(false)
    }
  }, [bindDoc])

  const loadDocument = useCallback(async (id: string) => {
    setOpening(true)
    try {
      const doc = await docosApi.getDocument(id)
      bindDoc(id, doc.graph, doc.title)
    } finally {
      setOpening(false)
    }
  }, [bindDoc])

  const runCommand = useCallback((command: string, options?: { track?: boolean }) => {
    if (!docId) return
    // Say so immediately. The first event cannot arrive until the planner has
    // answered, and a planner can take a minute or time out — during which the
    // panel used to read "Idle", so a command that was working looked dead.
    setPanel((s) => ({
      ...EMPTY_PANEL, task: command, currentAction: 'Planning…', history: s.history,
    }))
    setStatus('running')
    setDiff(null)
    setReview(null)

    // Undo, Redo and the timeline controls are not edits to review — they are
    // the review. Only an instruction the reader typed is tracked.
    if (options?.track !== false) {
      trackingRef.current = command
      beforeRef.current = versionsRef.current.find((v) => v.is_current)?.seq ?? null
    } else {
      trackingRef.current = null
      beforeRef.current = null
    }

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
        // The words are the same ones the rest of the app uses for the same
        // failure — a database outage should not read differently in here.
        .catch((e) => {
          const { title, detail } = explain(e, 'run that instruction')
          failed(`${title}. ${detail}`)
        })
    }
  }, [docId, enqueue])

  const undo = useCallback(() => runCommand('Undo', UNTRACKED), [runCommand])
  const redo = useCallback(() => runCommand('Redo', UNTRACKED), [runCommand])
  const rewind = useCallback((seq: number) => runCommand(`Rewind to version ${seq}`, UNTRACKED), [runCommand])
  const restore = useCallback((seq: number) => runCommand(`Restore version ${seq}`, UNTRACKED), [runCommand])
  const compare = useCallback((a: number, b: number) => runCommand(`Compare version ${a} and ${b}`, UNTRACKED), [runCommand])
  const clearDiff = useCallback(() => setDiff(null), [])

  /** Keep what the assistant did. Nothing to undo — the change is already in
   *  the document; this only takes the question off the screen. */
  const acceptChanges = useCallback(() => setReview(null), [])

  /** Put the document back as it was before the last instruction. */
  const rejectChanges = useCallback(() => {
    setReview(null)
    runCommand('Undo', UNTRACKED)
  }, [runCommand])

  /** Turn the canvas to a node — the outline clicking through to a heading.
   *  Local: nothing is sent, because nothing about the document changes. */
  const focusNode = useCallback((id: string) => setFocusId(id), [])

  /** Show exactly what the last instruction changed. */
  const showChanges = useCallback(() => {
    if (review) compare(review.before, review.after)
  }, [review, compare])

  return {
    docId, title, graph, status, connection, opening,
    selectedIds, activeId, focusId, removingIds, panel, versions, diff, review,
    importFile, loadDocument, runCommand, focusNode,
    undo, redo, rewind, restore, compare, clearDiff,
    acceptChanges, rejectChanges, showChanges,
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
