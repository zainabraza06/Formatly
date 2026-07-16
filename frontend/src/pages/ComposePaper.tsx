import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import { GlassCard } from '../components/GlassCard'
import { StyleManager } from '../components/paper/StyleManager'
import { SpecPreview } from '../components/paper/SpecPreview'
import {
  downloadBlob, paperApi,
  type ComposeRequest, type PaperSpec, type StyleSummary,
} from '../lib/paperApi'

const DOC_KINDS = ['paper', 'report', 'thesis chapter', 'white paper', 'case study']

export function ComposePaper() {
  const [styles, setStyles] = useState<StyleSummary[]>([])
  const [style, setStyle] = useState('report')
  const [docKind, setDocKind] = useState('paper')

  const [rawText, setRawText] = useState('')
  const [code, setCode] = useState('')
  const [results, setResults] = useState('')
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

  const buildRequest = (): ComposeRequest => ({
    raw_text: rawText,
    style,
    doc_kind: docKind,
    code: code.trim() || null,
    results: results.trim() || null,
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
            Give raw material — the AI writes the document, you get a formatted DOCX.
          </div>
        </div>
        <button
          onClick={() => setShowStyles((s) => !s)}
          className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-700 hover:bg-white/20 dark:bg-white/5 dark:text-neutral-200"
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
        {/* ── input ── */}
        <GlassCard className="space-y-3">
          <Field label="What is this? *" hint="Your raw text, notes, findings, data — anything.">
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={10}
              placeholder="Paste your raw notes, data, experiment description, findings…"
              className={area}
            />
          </Field>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Model results / data" hint="Numbers here become tables & charts.">
              <textarea value={results} onChange={(e) => setResults(e.target.value)} rows={5}
                        placeholder={'accuracy: CNN 0.94, LSTM 0.91, SVM 0.85\nepochs: 0.61, 0.79, 0.88, 0.94'}
                        className={area} />
            </Field>
            <Field label="Source code" hint="Informs the methodology section.">
              <textarea value={code} onChange={(e) => setCode(e.target.value)} rows={5}
                        placeholder="model = Sequential([...])" className={clsx(area, 'font-mono text-[11px]')} />
            </Field>
          </div>

          <Field label="Reference example" hint="A sample the writing should follow.">
            <textarea value={referenceExample} onChange={(e) => setReferenceExample(e.target.value)}
                      rows={3} placeholder="Paste an example paper/section to imitate…" className={area} />
          </Field>

          <Field label="Extra instructions">
            <input value={instructions} onChange={(e) => setInstructions(e.target.value)}
                   placeholder="e.g. emphasise the ablation study; keep it under 6 pages"
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

            <Field label="Document kind">
              <select value={docKind} onChange={(e) => setDocKind(e.target.value)} className={input}>
                {DOC_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
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
                       placeholder="Institution" className={input} />
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
            <GlassCard>
              <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.4 }}
                          className="text-xs text-neutral-500">
                Reading your material, planning sections and visualisations…
              </motion.div>
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
