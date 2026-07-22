import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import { GlassCard } from '../components/GlassCard'
import { StyleManager } from '../components/paper/StyleManager'
import { SpecPreview } from '../components/paper/SpecPreview'
import {
  downloadBlob, paperApi,
  type ComposeRequest, type Depth, type PaperSpec, type StyleSummary,
} from '../lib/paperApi'

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

// Established styles we have no stylesheet for, but whose conventions the writer
// knows. Suggestions only — any name can be typed.
const ESTABLISHED_STYLES = [
  'Chicago', 'Harvard', 'MLA', 'Vancouver', 'AMA', 'Turabian',
  'Oxford', 'AAA', 'ASA', 'Nature', 'Elsevier', 'Springer',
]

export function ComposePaper() {
  const [styles, setStyles] = useState<StyleSummary[]>([])
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

  const loadStyles = () => {
    paperApi.styles().then(setStyles).catch((e) => setError(e.message))
  }
  useEffect(loadStyles, [])

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
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">Compose</div>
          <div className="text-xs text-neutral-500">
            Describe what you need and give it your material — the AI writes the document,
            you get a formatted DOCX.
          </div>
        </div>
      </div>

      {showStyles && (
        <GlassCard>
          <StyleManager styles={styles} onChanged={loadStyles} />
        </GlassCard>
      )}

      {error && <div className="rounded-xl bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</div>}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_400px]">
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
                  className="text-[10px] font-semibold text-violet-600 hover:underline dark:text-violet-400"
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
                  <span className="mt-1 block text-[10px] text-neutral-400">
                    Its citation format and section conventions will be followed. Page
                    typography uses our standard layout — for exact typography, upload a
                    sample under <span className="font-medium">Manage / add styles</span>.
                  </span>
                </>
              )}
            </div>

            <Field label="Document kind" hint="Free text — anything you like.">
              <input value={docKind} onChange={(e) => setDocKind(e.target.value)}
                     list="doc-kinds" placeholder="report" className={input} />
              <datalist id="doc-kinds">
                {DOC_KINDS.map((k) => <option key={k} value={k} />)}
              </datalist>
            </Field>

            <Field label="Depth" hint={DEPTH_OPTIONS.find((d) => d.id === depth)?.hint}>
              <div className="flex gap-1">
                {DEPTH_OPTIONS.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => setDepth(d.id)}
                    className={clsx(
                      'flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors',
                      depth === d.id
                        ? 'border-violet-500/40 bg-violet-500/15 text-violet-700 dark:text-violet-300'
                        : 'border-white/10 bg-white/5 text-neutral-500 hover:bg-white/10',
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
                className="flex-1 rounded-xl bg-neutral-900 px-4 py-2.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-50 dark:bg-white dark:text-neutral-950"
              >
                {busy === 'generating' ? 'Writing…' : spec ? 'Regenerate' : 'Generate'}
              </button>
              <button
                onClick={download}
                disabled={busy !== 'idle' || !rawText.trim()}
                className="flex-1 rounded-xl border border-white/10 bg-white/10 px-4 py-2.5 text-xs font-semibold text-neutral-700 hover:bg-white/20 disabled:opacity-50 dark:bg-white/5 dark:text-neutral-200"
              >
                {busy === 'rendering' ? 'Rendering…' : 'Download DOCX'}
              </button>
            </div>
            <div className="text-[10px] text-neutral-500">
              Rendering as <span className="font-semibold">{styleName}</span>
              {provider && <> · written by <span className="font-semibold">{provider}</span></>}
            </div>
          </GlassCard>

          {busy === 'generating' && (
            <GlassCard className="space-y-1">
              <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.4 }}
                          className="text-xs text-neutral-500">
                Reading your material, planning sections and visualisations…
              </motion.div>
              {depth === 'detailed' && (
                <div className="text-[10px] text-neutral-400">
                  Detailed documents are planned first, then written one section at a time,
                  so this takes a few minutes. Leave the tab open.
                </div>
              )}
            </GlassCard>
          )}

          {spec && <SpecPreview spec={spec} />}
        </div>
      </div>
    </div>
  )
}

const input =
  'w-full rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-sm text-neutral-900 outline-none placeholder:text-neutral-500 focus:ring-2 focus:ring-violet-400/30 dark:bg-white/5 dark:text-neutral-100'
const area = clsx(input, 'resize-y leading-relaxed')

// A <select>'s native option list is drawn by the OS, which ignores translucent
// backgrounds — `bg-white/10` left white text on white in dark mode. Selects and
// their options need opaque colours of their own.
const select =
  'w-full rounded-xl border border-white/10 bg-white px-3 py-2 text-sm text-neutral-900 outline-none focus:ring-2 focus:ring-violet-400/30 dark:border-white/10 dark:bg-neutral-900 dark:text-neutral-100'
const option = 'bg-white text-neutral-900 dark:bg-neutral-900 dark:text-neutral-100'

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
        {label}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[10px] text-neutral-400">{hint}</span>}
    </label>
  )
}
