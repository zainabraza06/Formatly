import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import { GlassCard } from '../components/GlassCard'
import { StyleManager } from '../components/paper/StyleManager'
import { SpecPreview } from '../components/paper/SpecPreview'
import {
  downloadBlob, paperApi,
  type Attachment, type ComposeRequest, type Depth, type PaperSpec, type StyleSummary,
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

// Starting points for labelling extra material. Users can type any label.
const LABEL_IDEAS = [
  'Data', 'Results', 'Survey responses', 'Interview transcript',
  'Source code', 'Financials', 'Citations', 'Meeting notes', 'Specifications',
]

let attachSeq = 0
const newAttachment = (label = ''): Attachment & { key: number } =>
  ({ key: ++attachSeq, label, content: '' })

export function ComposePaper() {
  const [styles, setStyles] = useState<StyleSummary[]>([])
  const [style, setStyle] = useState('report')
  const [docKind, setDocKind] = useState('report')
  const [depth, setDepth] = useState<Depth>('standard')

  const [rawText, setRawText] = useState('')
  const [attachments, setAttachments] = useState<(Attachment & { key: number })[]>([])
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

  const addAttachment = (label = '') =>
    setAttachments((a) => [...a, newAttachment(label)])
  const updateAttachment = (key: number, patch: Partial<Attachment>) =>
    setAttachments((a) => a.map((x) => (x.key === key ? { ...x, ...patch } : x)))
  const removeAttachment = (key: number) =>
    setAttachments((a) => a.filter((x) => x.key !== key))

  const buildRequest = (): ComposeRequest => ({
    raw_text: rawText,
    style,
    doc_kind: docKind,
    depth,
    attachments: attachments
      .filter((a) => a.content.trim())
      .map(({ label, content }) => ({ label: label.trim() || 'additional material', content })),
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

  const styleName = styles.find((s) => s.id === style)?.name || style

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
        <button
          onClick={() => setShowStyles((s) => !s)}
          className="shrink-0 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-700 hover:bg-white/20 dark:bg-white/5 dark:text-neutral-200"
        >
          {showStyles ? 'Hide styles' : 'Manage styles'}
        </button>
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
            hint="Anything: notes, findings, a brief, raw text. Say what you want written."
          >
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={12}
              placeholder={
                'e.g. "Write a report on our Q3 customer churn analysis…"\n' +
                'or paste the notes, brief, findings or transcript you want written up.'
              }
              className={area}
            />
          </Field>

          {/* arbitrary labelled extra material */}
          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
                Extra material
              </span>
              <span className="text-[10px] text-neutral-400">optional · add as many as you need</span>
            </div>

            {attachments.length === 0 && (
              <div className="rounded-xl border border-dashed border-white/15 p-3 text-center">
                <div className="text-[11px] text-neutral-500">
                  Add data, a transcript, code, citations — anything the document should draw on.
                  <br />
                  <span className="text-neutral-400">
                    Numbers you include here become tables and charts automatically.
                  </span>
                </div>
              </div>
            )}

            <div className="space-y-2">
              {attachments.map((a) => (
                <motion.div
                  key={a.key}
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-white/10 bg-white/5 p-2"
                >
                  <div className="mb-1.5 flex items-center gap-2">
                    <input
                      value={a.label}
                      onChange={(e) => updateAttachment(a.key, { label: e.target.value })}
                      list="attachment-labels"
                      placeholder="Label (e.g. Results, Transcript, Code)"
                      className="flex-1 rounded-lg border border-white/10 bg-white/10 px-2 py-1 text-[11px] font-medium text-neutral-900 outline-none dark:bg-white/5 dark:text-neutral-100"
                    />
                    <button
                      onClick={() => removeAttachment(a.key)}
                      className="rounded px-1.5 text-neutral-400 hover:text-red-500"
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                  <textarea
                    value={a.content}
                    onChange={(e) => updateAttachment(a.key, { content: e.target.value })}
                    rows={4}
                    placeholder="Paste this material…"
                    className={clsx(area, 'text-[11px]')}
                  />
                </motion.div>
              ))}
            </div>

            <datalist id="attachment-labels">
              {LABEL_IDEAS.map((l) => <option key={l} value={l} />)}
            </datalist>

            <div className="mt-2 flex flex-wrap gap-1.5">
              <button
                onClick={() => addAttachment()}
                className="rounded-lg border border-white/10 bg-white/10 px-2.5 py-1 text-[11px] font-semibold text-neutral-700 hover:bg-white/20 dark:bg-white/5 dark:text-neutral-200"
              >
                + Add material
              </button>
              {LABEL_IDEAS.slice(0, 5).map((l) => (
                <button
                  key={l}
                  onClick={() => addAttachment(l)}
                  className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-neutral-500 hover:bg-white/10 dark:text-neutral-400"
                >
                  + {l}
                </button>
              ))}
            </div>
          </div>

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
            <Field label="Style">
              <select value={style} onChange={(e) => setStyle(e.target.value)} className={input}>
                <optgroup label="Built-in">
                  {styles.filter((s) => s.builtin === 'true').map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.columns} col)</option>
                  ))}
                </optgroup>
                {styles.some((s) => s.builtin === 'false') && (
                  <optgroup label="My styles">
                    {styles.filter((s) => s.builtin === 'false').map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </optgroup>
                )}
              </select>
            </Field>

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
