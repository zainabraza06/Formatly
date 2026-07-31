import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { GlassCard } from '../components/GlassCard'
import { DocumentPreview } from '../components/paper/DocumentPreview'
import { GenerationStatus } from '../components/paper/GenerationStatus'
import { StyleManager } from '../components/paper/StyleManager'
import {
  downloadBlob, paperApi,
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
  { id: 'detailed', label: 'Detailed', hint: 'in-depth, written section by section — slower' },
]

// Suggestions only — the field is free text, so any document kind works.
const DOC_KINDS = [
  'paper', 'report', 'literature review', 'case study', 'proposal',
  'memo', 'white paper', 'technical documentation', 'essay', 'thesis chapter',
]

// Sentinel for the "name your own style" option.
const OTHER = '__other__'
// Sentinel for a document kind not in the list.
const CUSTOM_KIND = '__custom_kind__'

// The built-in styles are fixed and always available, so the dropdown seeds with
// them and never collapses to a single option if the styles request hiccups. A
// successful fetch replaces this with the server list (which also carries the
// user's custom styles).
const BUILTIN_STYLES: StyleSummary[] = [
  { id: 'ieee', name: 'IEEE Conference', columns: '2', builtin: 'true', derived_from: '', detected: '', heading_scheme: 'roman_alpha', table_borders: 'horizontal' },
  { id: 'apa', name: 'APA 7th Edition', columns: '1', builtin: 'true', derived_from: '', detected: '', heading_scheme: 'none', table_borders: 'horizontal' },
  { id: 'acm', name: 'ACM (sigconf)', columns: '2', builtin: 'true', derived_from: '', detected: '', heading_scheme: 'decimal', table_borders: 'horizontal' },
  { id: 'report', name: 'Technical Report', columns: '1', builtin: 'true', derived_from: '', detected: '', heading_scheme: 'decimal', table_borders: 'grid' },
]

// Established styles we have no stylesheet for, but whose conventions the writer
// knows. Suggestions only — any name can be typed.
const ESTABLISHED_STYLES = [
  'Chicago', 'Harvard', 'MLA', 'Vancouver', 'AMA', 'Turabian',
  'Oxford', 'AAA', 'ASA', 'Nature', 'Elsevier', 'Springer',
]

export function ComposePaper() {
  const [styles, setStyles] = useState<StyleSummary[]>(BUILTIN_STYLES)
  const [style, setStyle] = useState('report')
  const [isOther, setIsOther] = useState(false)
  const [otherStyle, setOtherStyle] = useState('')
  const [docKind, setDocKind] = useState('report')
  const [depth, setDepth] = useState<Depth>('standard')

  const [rawText, setRawText] = useState('')
  const [referenceExample, setReferenceExample] = useState('')
  const [instructions, setInstructions] = useState('')
  const [titleHint, setTitleHint] = useState('')
  const [authorName, setAuthorName] = useState('')
  const [authorAffil, setAuthorAffil] = useState('')

  const [spec, setSpec] = useState<PaperSpec | null>(null)
  const [provider, setProvider] = useState('')
  const [busy, setBusy] = useState<'idle' | 'generating' | 'rendering'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [showStyles, setShowStyles] = useState(false)

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
    let cancelled = false
    let url: string | null = null
    setPdfState('loading')
    paperApi.previewPdf(spec)
      .then((b) => {
        if (cancelled) return
        url = URL.createObjectURL(b)
        setPdfUrl(url)
        setPdfState('ready')
      })
      .catch(() => { if (!cancelled) setPdfState('unavailable') })
    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
  }, [spec])

  // Everything goes in one box. The API still accepts labelled attachments —
  // the CLI uses them for files — but the UI should not make a person decide
  // which bucket their notes belong in.
  // An "other" style is sent by name: the backend has no stylesheet for it, so it
  // instructs the writer to follow that style's conventions instead.
  const effectiveStyle = isOther ? (otherStyle.trim() || 'report') : style

  const buildRequest = (): ComposeRequest => ({
    raw_text: rawText,
    style: effectiveStyle,
    doc_kind: docKind,
    depth,
    reference_example: referenceExample.trim() || null,
    instructions: instructions.trim() || null,
    title_hint: titleHint.trim() || null,
    authors: authorName.trim()
      ? [{ name: authorName.trim(), affiliation: authorAffil.trim() }]
      : [],
  })

  const generate = async () => {
    if (!rawText.trim()) return
    setBusy('generating')
    setError(null)
    setSpec(null)
    try {
      const res = await paperApi.generate(buildRequest())
      setSpec(res.spec)
      setProvider(res.provider)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed')
    } finally {
      setBusy('idle')
    }
  }

  const download = async () => {
    setBusy('rendering')
    setError(null)
    try {
      const b = spec
        ? await paperApi.renderSpec(spec)
        : await paperApi.compose(buildRequest())
      downloadBlob(b, `${(spec?.meta.title || titleHint || 'document').slice(0, 60)}.docx`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Render failed')
    } finally {
      setBusy('idle')
    }
  }

  const styleName = isOther
    ? (otherStyle.trim() || 'standard layout')
    : (styles.find((s) => s.id === style)?.name || style)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Compose</h1>
        <p className="mt-0.5 text-sm text-muted">
          Describe what you need and give it your material — the AI writes the document,
          you get a formatted DOCX.
        </p>
      </div>

      {showStyles && (
        <GlassCard>
          <StyleManager styles={styles} onChanged={loadStyles} />
        </GlassCard>
      )}

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

          <Field label="Reference example" hint="A sample whose writing style should be followed.">
            <textarea value={referenceExample} onChange={(e) => setReferenceExample(e.target.value)}
                      rows={3} placeholder="Paste an example document or section to imitate…"
                      className={area} />
          </Field>

          <Field label="Extra instructions">
            <input value={instructions} onChange={(e) => setInstructions(e.target.value)}
                   placeholder="e.g. emphasise the cost savings; keep it under 4 pages"
                   className={input} />
          </Field>
        </GlassCard>

        {/* ── settings + actions ── */}
        <div className="space-y-4">
          <GlassCard className="space-y-3">
            <div>
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
                  Style
                </span>
                <button
                  onClick={() => setShowStyles((s) => !s)}
                  className="text-[11px] font-medium text-ink underline-offset-2 hover:underline"
                >
                  {showStyles ? 'Hide manager' : 'Manage / add styles'}
                </button>
              </div>

              <select
                value={isOther ? OTHER : style}
                onChange={(e) => {
                  const v = e.target.value
                  if (v === OTHER) {
                    setIsOther(true)
                  } else {
                    setIsOther(false)
                    setStyle(v)
                  }
                }}
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
                <optgroup label="Other">
                  <option value={OTHER} className={option}>Another style — name it…</option>
                </optgroup>
              </select>

              {isOther && (
                <>
                  <input
                    value={otherStyle}
                    onChange={(e) => setOtherStyle(e.target.value)}
                    list="known-styles"
                    placeholder="e.g. Chicago, Harvard, MLA, Vancouver, AMA"
                    className={clsx(input, 'mt-2')}
                  />
                  <datalist id="known-styles">
                    {ESTABLISHED_STYLES.map((s) => <option key={s} value={s} />)}
                  </datalist>
                  <span className="mt-1 block text-[10px] text-faint">
                    Its citation format and section conventions will be followed. Page
                    typography uses our standard layout — for exact typography, upload a
                    sample under <span className="font-medium text-muted">Manage / add styles</span>.
                  </span>
                </>
              )}
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
              <button
                onClick={generate}
                disabled={busy !== 'idle' || !rawText.trim()}
                className={`${btnPrimary} flex-1`}
              >
                {busy === 'generating' ? 'Writing…' : spec ? 'Regenerate' : 'Generate'}
              </button>
              <button
                onClick={download}
                disabled={busy !== 'idle' || !rawText.trim()}
                className={`${btnGhost} flex-1`}
              >
                {busy === 'rendering' ? 'Rendering…' : 'Download DOCX'}
              </button>
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
            depth={depth}
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
