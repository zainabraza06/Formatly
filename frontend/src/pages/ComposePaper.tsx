import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import { GlassCard } from '../components/GlassCard'
import { DocumentPreview } from '../components/paper/DocumentPreview'
import { GenerationStatus } from '../components/paper/GenerationStatus'
import {
  downloadBlob, isAbort, paperApi,
  type ComposeRequest, type Depth, type PaperSpec, type StyleSummary,
} from '../lib/paperApi'
import {
  btnGhost, btnPrimary,
  field as uiField, select as uiSelect, selectOption as uiSelectOption,
  textarea as uiTextarea,
} from '../lib/ui'

// A model left to itself writes concisely, so depth has to be asked for.
// "detailed" is written section-by-section because one call cannot hold it.
const DEPTH_OPTIONS: { id: Depth; label: string; hint: string }[] = [
  { id: 'brief', label: 'Brief', hint: '1–2 paragraphs per section' },
  { id: 'standard', label: 'Standard', hint: '2–3 paragraphs per section' },
]

// Suggestions only — the field is free text, so any document kind works.
const DOC_KINDS = [
  'paper', 'report', 'assignment', 'literature review', 'case study', 'proposal',
  'memo', 'white paper', 'technical documentation', 'essay', 'thesis chapter',
]

// Sentinel for a document kind not in the list.
const CUSTOM_KIND = '__custom_kind__'

const BUILTIN_STYLES: StyleSummary[] = [
  { id: 'ieee', name: 'IEEE Conference (2-Column)', columns: '2', builtin: 'true', heading_scheme: 'roman_alpha', table_borders: 'horizontal' },
  { id: 'ieee_1col', name: 'IEEE Conference (1-Column)', columns: '1', builtin: 'true', heading_scheme: 'roman_alpha', table_borders: 'horizontal' },
  { id: 'assignment', name: 'Formal Assignment', columns: '1', builtin: 'true', heading_scheme: 'decimal', table_borders: 'grid' },
]

export function ComposePaper() {
  const [styles, setStyles] = useState<StyleSummary[]>(BUILTIN_STYLES)
  const [style, setStyle] = useState('ieee')
  const [docKind, setDocKind] = useState('paper')
  const [depth, setDepth] = useState<Depth>('standard')

  const [rawText, setRawText] = useState('')
  const [instructions, setInstructions] = useState('')
  const [titleHint, setTitleHint] = useState('')
  const [authorName, setAuthorName] = useState('')
  const [authorAffil, setAuthorAffil] = useState('')

  const [spec, setSpec] = useState<PaperSpec | null>(null)
  const [provider, setProvider] = useState('')
  const [busy, setBusy] = useState<'idle' | 'generating' | 'rendering'>('idle')
  const [error, setError] = useState<string | null>(null)

  // Held for as long as a run is in flight, so Stop has something to abort.
  const runRef = useRef<AbortController | null>(null)

  // Exact preview: the real DOCX rendered to PDF. Falls back to the HTML view
  // while it renders, or if LibreOffice is unavailable.
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfState, setPdfState] = useState<'idle' | 'loading' | 'ready' | 'unavailable'>('idle')

  const loadStyles = () => {
    // Only replace the seeded built-ins when the server actually returns styles;
    // a failure keeps the built-ins visible rather than emptying the dropdown.
    paperApi.styles()
      .then((list) => { if (list.length) setStyles(list) })
      .catch(() => {})
  }
  useEffect(loadStyles, [])

  // Fetch the exact PDF whenever a new spec is ready.
  useEffect(() => {
    if (!spec) { setPdfUrl(null); setPdfState('idle'); return }
    // Aborted on cleanup: a superseded preview would otherwise keep the server
    // busy rendering a PDF nobody is waiting for any more.
    const run = new AbortController()
    let url: string | null = null
    setPdfState('loading')
    paperApi.previewPdf(spec, undefined, run.signal)
      .then((b) => {
        if (run.signal.aborted) return
        url = URL.createObjectURL(b)
        setPdfUrl(url)
        setPdfState('ready')
      })
      .catch((e) => { if (!isAbort(e)) setPdfState('unavailable') })
    return () => {
      run.abort()
      if (url) URL.revokeObjectURL(url)
    }
  }, [spec])

  // Everything goes in one box. The API still accepts labelled attachments —
  // the CLI uses them for files — but the UI should not make a person decide
  // which bucket their notes belong in.
  const buildRequest = (): ComposeRequest => ({
    raw_text: rawText,
    style,
    doc_kind: docKind,
    depth,
    instructions: instructions.trim() || null,
    title_hint: titleHint.trim() || null,
    authors: authorName.trim()
      ? [{ name: authorName.trim(), affiliation: authorAffil.trim() }]
      : [],
  })

  // Abandoning a run is the user's decision, so it is not reported as a failure.
  const stop = () => {
    runRef.current?.abort()
    runRef.current = null
    setBusy('idle')
  }

  const generate = async () => {
    if (!rawText.trim()) return
    const run = new AbortController()
    runRef.current = run
    setBusy('generating')
    setError(null)
    setSpec(null)
    try {
      const res = await paperApi.generate(buildRequest(), run.signal)
      setSpec(res.spec)
      setProvider(res.provider)
    } catch (e) {
      if (!isAbort(e)) setError(e instanceof Error ? e.message : 'Generation failed')
    } finally {
      if (runRef.current === run) {
        runRef.current = null
        setBusy('idle')
      }
    }
  }

  const download = async () => {
    const run = new AbortController()
    runRef.current = run
    setBusy('rendering')
    setError(null)
    try {
      const b = spec
        ? await paperApi.renderSpec(spec, undefined, run.signal)
        : await paperApi.compose(buildRequest(), run.signal)
      downloadBlob(b, `${(spec?.meta.title || titleHint || 'document').slice(0, 60)}.docx`)
    } catch (e) {
      if (!isAbort(e)) setError(e instanceof Error ? e.message : 'Render failed')
    } finally {
      if (runRef.current === run) {
        runRef.current = null
        setBusy('idle')
      }
    }
  }

  const styleName = styles.find((s) => s.id === style)?.name || style

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Compose</h1>
        <p className="mt-0.5 text-sm text-muted">
          Describe what you need and give it your material — the AI writes the document,
          you get a formatted DOCX.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_400px]">
        {/* ── material ── */}
        <GlassCard className="space-y-3">
          <Field
            label="Your material *"
            hint="Everything goes here: what you want written, plus any notes, data, transcripts or code it should draw on. Numbers become tables and charts automatically."
          >
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={20}
              placeholder={`Say what you need, then paste everything it should be based on. For example:

Write a report on our Q3 customer churn for the leadership team.

Survey: 412 cancelling customers. Price 63%, missing features 21%, support 11%, other 5%.
Churn by month: July 4.2%, August 5.1%, September 6.8%.
Interview: "The renewal price jumped 40% with no warning."`}
              className={area}
            />
          </Field>

          <Field
            label="Extra instructions"
            hint="Followed as written, and they override the defaults. One per line is fine."
          >
            <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)}
                      rows={3}
                      placeholder={`e.g. Bold the important keywords and technical terms.
Keep it under 4 pages.
Write in the first person plural.`}
                      className={area} />
          </Field>
        </GlassCard>

        {/* ── settings + actions ── */}
        <div className="space-y-4">
          <GlassCard className="space-y-3">
            <div>
              <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
                Style
              </span>

              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className={select}
              >
                <optgroup label="Built-in">
                  {styles.filter((s) => s.builtin === 'true').map((s) => (
                    <option key={s.id} value={s.id} className={option}>
                      {s.name} ({s.columns} col)
                    </option>
                  ))}
                </optgroup>
                {styles.some((s) => s.builtin === 'false') && (
                  <optgroup label="My styles">
                    {styles.filter((s) => s.builtin === 'false').map((s) => (
                      <option key={s.id} value={s.id} className={option}>{s.name}</option>
                    ))}
                  </optgroup>
                )}
              </select>
            </div>

            <Field label="Document kind">
              <select
                value={DOC_KINDS.includes(docKind) ? docKind : CUSTOM_KIND}
                onChange={(e) => {
                  const v = e.target.value
                  setDocKind(v === CUSTOM_KIND ? '' : v)
                }}
                className={select}
              >
                {DOC_KINDS.map((k) => (
                  <option key={k} value={k} className={option}>
                    {k.charAt(0).toUpperCase() + k.slice(1)}
                  </option>
                ))}
                <option value={CUSTOM_KIND} className={option}>Something else…</option>
              </select>
              {!DOC_KINDS.includes(docKind) && (
                <input
                  value={docKind}
                  onChange={(e) => setDocKind(e.target.value)}
                  placeholder="e.g. grant proposal, policy brief"
                  className={`${input} mt-2`}
                />
              )}
            </Field>

            <Field label="Depth" hint={DEPTH_OPTIONS.find((d) => d.id === depth)?.hint}>
              <div className="flex gap-1">
                {DEPTH_OPTIONS.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => setDepth(d.id)}
                    className={clsx(
                      'flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-medium transition-colors',
                      depth === d.id
                        ? 'border-ink bg-accent text-accent-fg'
                        : 'border-line bg-surface text-muted hover:bg-surface-2 hover:text-ink',
                    )}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Title hint">
              <input value={titleHint} onChange={(e) => setTitleHint(e.target.value)}
                     placeholder="Leave blank to let the AI title it" className={input} />
            </Field>

            <div className="grid grid-cols-2 gap-2">
              <Field label="Author">
                <input value={authorName} onChange={(e) => setAuthorName(e.target.value)}
                       placeholder="Your name" className={input} />
              </Field>
              <Field label="Affiliation">
                <input value={authorAffil} onChange={(e) => setAuthorAffil(e.target.value)}
                       placeholder="Organisation" className={input} />
              </Field>
            </div>

            <div className="flex gap-2 pt-1">
              {/* While a run is in flight the only useful action is calling it
                  off, so Stop replaces the rest. There is nothing to download
                  until something has been written, so that button waits. */}
              {busy !== 'idle' ? (
                <button onClick={stop} className={`${btnGhost} flex-1`}>
                  Stop
                </button>
              ) : (
                <>
                  <button
                    onClick={generate}
                    disabled={!rawText.trim()}
                    className={`${btnPrimary} flex-1`}
                  >
                    {spec ? 'Regenerate' : 'Generate'}
                  </button>
                  {spec && (
                    <button onClick={download} className={`${btnGhost} flex-1`}>
                      Download DOCX
                    </button>
                  )}
                </>
              )}
            </div>
            <div className="text-[10px] text-faint">
              Rendering as <span className="font-medium text-muted">{styleName}</span>
              {provider && <> · written by <span className="font-medium text-muted">{provider}</span></>}
            </div>
          </GlassCard>

          {/* Working / error status appears right where the result will, so
              attention stays in one place instead of jumping to the top. */}
          <GenerationStatus
            state={
              busy === 'generating' || (busy === 'rendering' && !spec)
                ? 'generating'
                : error
                  ? 'error'
                  : null
            }
            error={error}
            onRetry={generate}
          />
        </div>
      </div>

      {/* ── finished document, rendered in full ── */}
      {spec && busy !== 'generating' && !error && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
                Preview
                <span className={clsx(
                  'rounded-full px-2 py-0.5 text-[10px] font-medium',
                  pdfState === 'ready'
                    ? 'bg-ink/10 text-ink'
                    : 'border border-line text-muted',
                )}>
                  {pdfState === 'ready' ? 'Exact document' : pdfState === 'loading' ? 'Rendering exact…' : 'Reading view'}
                </span>
              </h2>
              <p className="text-xs text-muted">
                {styleName}{provider && <> · written by <span className="font-medium">{provider}</span></>}
              </p>
            </div>
            <button
              onClick={download}
              disabled={busy !== 'idle'}
              className={`${btnPrimary} px-5`}
            >
              {busy === 'rendering' ? 'Preparing…' : 'Download DOCX'}
            </button>
          </div>

          {pdfState === 'ready' && pdfUrl ? (
            <iframe
              title="Exact document preview"
              src={pdfUrl}
              className="h-[80vh] w-full rounded-xl border border-line bg-white"
            />
          ) : (
            <div className="max-h-[80vh] overflow-auto rounded-xl border border-line bg-neutral-200/60 p-4 dark:bg-neutral-800/50 sm:p-8">
              {pdfState === 'unavailable' && (
                <div className="mb-3 text-center text-[11px] text-muted">
                  Showing a reading view — the exact document render needs LibreOffice on the server.
                </div>
              )}
              <DocumentPreview spec={spec} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const input = uiField
const area = uiTextarea
const select = uiSelect
const option = uiSelectOption

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-muted">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[10px] text-faint">{hint}</span>}
    </label>
  )
}
