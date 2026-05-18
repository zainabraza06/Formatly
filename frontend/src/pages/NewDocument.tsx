import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GlassCard } from '../components/GlassCard'
import { PipelineSteps } from '../components/PipelineSteps'
import { PreviewPanel } from '../components/PreviewPanel'
import { SectionEditor } from '../components/SectionEditor'
import { StylePresets } from '../components/StylePresets'
import { UploadDropzone } from '../components/UploadDropzone'
import { api } from '../lib/api'
import type {
  ChartKind,
  ChartSpec,
  Draft,
  DocumentSection,
  GenerateRequest,
  GenerateResponse,
  StylePreset,
  TemplateAnalyzeResponse,
  Tone,
} from '../types/api'

const DEFAULT_PROMPT =
  'Create a report on climate change. Include a title page, table of contents, clear sections, a short summary, and a conclusion.'

const DEFAULT_FORMAT =
  'Times New Roman\nHeading size 16 bold\n1.5 spacing\n1 inch margins\nInclude charts'

function toDraft(
  r: GenerateResponse,
  req: GenerateRequest,
  template?: TemplateAnalyzeResponse | null,
): Draft {
  return {
    document_id: r.document_id,
    title: r.title,
    outline: r.outline,
    sections: r.sections,
    extracted_rules: r.extracted_rules,
    style_preset: req.style_preset,
    tone: req.tone,
    template_id: template?.template_id || req.template_id || null,
    template_style: template?.extracted_style || {},
    include_title_page: req.include_title_page,
    include_toc: req.include_toc,
    suggested_charts: r.suggested_charts,
  }
}

// ── Small sub-components ─────────────────────────────────────────────────────

function ExportButtons({ documentId }: { documentId: string }) {
  const docx  = api.exportDocxUrl(documentId)
  const pdf   = api.exportPdfUrl(documentId)
  const excel = api.exportExcelUrl(documentId)

  return (
    <div className="flex flex-wrap gap-2">
      <a
        href={docx}
        className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
      >
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor">
          <path d="M9.5 1.5v3h3L9.5 1.5zm-1 0H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6h-3.5V1.5z" />
        </svg>
        DOCX
      </a>
      <a
        href={pdf}
        className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
      >
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor">
          <path d="M9.5 1.5v3h3L9.5 1.5zm-1 0H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6h-3.5V1.5z" />
        </svg>
        PDF
      </a>
      <a
        href={excel}
        className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
      >
        <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor">
          <path d="M14 2H6L2 6v8a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1zm-4 9H7v-1h3v1zm2-2H7V8h5v1z" />
        </svg>
        Excel
      </a>
    </div>
  )
}

function ChartCard({
  chart,
  index,
  documentId,
  onRemove,
  onAdd,
  isAdded,
}: {
  chart: ChartSpec
  index: number
  documentId: string | undefined
  onRemove: () => void
  onAdd: () => void
  isAdded: boolean
}) {
  const [imgKey, setImgKey] = useState(0)
  const [rendered, setRendered] = useState(false)
  const [rendering, setRendering] = useState(false)
  const [imgError, setImgError] = useState(false)

  async function handleRender() {
    if (!documentId) return
    setRendering(true)
    try {
      await api.renderChart(documentId, index, chart)
      setImgKey((k) => k + 1)
      setRendered(true)
      setImgError(false)
    } finally {
      setRendering(false)
    }
  }

  const imgUrl = documentId
    ? `${api.chartImageUrl(documentId, index)}?v=${imgKey}`
    : null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold text-neutral-900 dark:text-neutral-100">
            {chart.title || `Chart ${index}`}
          </div>
          <div className="mt-0.5 text-neutral-500 dark:text-neutral-400">
            {chart.kind} · {chart.labels.length} data points
          </div>
          {chart.explanation ? (
            <div className="mt-1 text-neutral-600 dark:text-neutral-400 italic">
              {chart.explanation}
            </div>
          ) : null}
        </div>
        <div className="flex shrink-0 gap-1.5">
          {documentId ? (
            <button
              type="button"
              disabled={rendering}
              onClick={handleRender}
              className="rounded-lg border border-white/10 bg-sky-500/10 px-2 py-1 text-[11px] text-sky-600 hover:bg-sky-500/20 disabled:opacity-50 dark:text-sky-400"
            >
              {rendering ? '…' : 'Preview'}
            </button>
          ) : null}
          <button
            type="button"
            onClick={isAdded ? onRemove : onAdd}
            className={`rounded-lg border border-white/10 px-2 py-1 text-[11px] ${
              isAdded
                ? 'bg-rose-500/10 text-rose-500 hover:bg-rose-500/20'
                : 'bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400'
            }`}
          >
            {isAdded ? 'Remove' : 'Add to doc'}
          </button>
        </div>
      </div>

      {rendered && imgUrl && !imgError ? (
        <div className="mt-3 overflow-hidden rounded-lg border border-white/10">
          <img
            key={imgKey}
            src={imgUrl}
            alt={chart.title || 'Chart preview'}
            className="w-full object-contain"
            onError={() => setImgError(true)}
          />
          <div className="flex justify-end border-t border-white/10 p-1">
            <a
              href={imgUrl}
              download={`chart-${index}.png`}
              className="rounded px-2 py-0.5 text-[10px] text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            >
              Download PNG
            </a>
          </div>
        </div>
      ) : null}
    </motion.div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function NewDocument() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT)
  const [formatting, setFormatting] = useState(DEFAULT_FORMAT)
  const [preset, setPreset] = useState<StylePreset>('business')
  const [tone, setTone] = useState<Tone>('formal')

  const [includeTitlePage, setIncludeTitlePage] = useState(true)
  const [includeToc, setIncludeToc] = useState(true)
  const [includeCharts, setIncludeCharts] = useState(true)

  const [template, setTemplate] = useState<TemplateAnalyzeResponse | null>(null)

  // User-composed manual charts
  const [manualCharts, setManualCharts] = useState<ChartSpec[]>([])
  const [newChartKind, setNewChartKind] = useState<ChartKind>('bar')

  // AI-suggested charts from document analysis
  const [suggestedCharts, setSuggestedCharts] = useState<ChartSpec[]>([])
  // Which suggested chart indices are added to the export
  const [addedSuggested, setAddedSuggested] = useState<Set<number>>(new Set())

  const [busy, setBusy] = useState(false)
  const [busyAnalyze, setBusyAnalyze] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [generated, setGenerated] = useState<GenerateResponse | null>(null)
  const [pipeline, setPipeline] = useState<GenerateResponse['pipeline']>([])
  const [sections, setSections] = useState<DocumentSection[]>([])

  const [busyRewrite, setBusyRewrite] = useState<{ id: string; tone: Tone } | null>(null)

  const documentId = generated?.document_id

  const autosaveTimer = useRef<number | null>(null)

  // Autosave draft whenever key state changes
  useEffect(() => {
    if (!documentId) return

    const draft: Draft = {
      document_id: documentId,
      title: generated?.title || 'Untitled Document',
      outline: generated?.outline || [],
      sections,
      extracted_rules: generated?.extracted_rules || {},
      style_preset: preset,
      tone,
      template_id: template?.template_id || null,
      template_style: template?.extracted_style || {},
      include_title_page: includeTitlePage,
      include_toc: includeToc,
      suggested_charts: suggestedCharts,
    }

    if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current)
    autosaveTimer.current = window.setTimeout(() => {
      api.saveDraft(documentId, draft).catch(() => {})
    }, 700)

    return () => {
      if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current)
    }
  }, [
    documentId,
    generated?.title,
    generated?.outline,
    generated?.extracted_rules,
    preset,
    tone,
    template,
    includeTitlePage,
    includeToc,
    sections,
    suggestedCharts,
  ])

  async function onGenerate() {
    setError(null)
    setBusy(true)
    setSuggestedCharts([])
    setAddedSuggested(new Set())
    try {
      const allCharts = [...manualCharts]
      const req: GenerateRequest = {
        prompt,
        formatting_instructions: formatting,
        style_preset: preset,
        tone,
        include_title_page: includeTitlePage,
        include_toc: includeToc,
        include_charts: includeCharts,
        charts: includeCharts ? allCharts : [],
        template_id: template?.template_id || null,
      }
      const r = await api.generate(req)
      setGenerated(r)
      setPipeline(r.pipeline)
      setSections(r.sections)
      if (r.suggested_charts?.length) {
        setSuggestedCharts(r.suggested_charts)
      }

      const draft = toDraft(r, req, template)
      await api.saveDraft(r.document_id, draft)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed')
    } finally {
      setBusy(false)
    }
  }

  async function onAnalyzeCharts() {
    if (!documentId) return
    setBusyAnalyze(true)
    try {
      const res = await api.analyzeCharts(documentId)
      if (res.suggested_charts?.length) {
        setSuggestedCharts(res.suggested_charts)
        setAddedSuggested(new Set())
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chart analysis failed')
    } finally {
      setBusyAnalyze(false)
    }
  }

  async function uploadTemplate(file: File) {
    const analysis = await api.uploadTemplate(file)
    setTemplate(analysis)
    return analysis
  }

  async function rewrite(sectionId: string, nextTone: Tone) {
    if (!documentId) return
    setBusyRewrite({ id: sectionId, tone: nextTone })
    try {
      const res = await api.rewriteSection(documentId, sectionId, nextTone)
      setSections((prev) =>
        prev.map((s) => (s.id === sectionId ? { ...s, content: res.section.content } : s)),
      )
    } finally {
      setBusyRewrite(null)
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {/* ── Left column: inputs ────────────────────────────────────────────── */}
      <div className="space-y-4">
        {/* Prompt */}
        <GlassCard>
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Prompt</div>
              <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
                Describe what to generate. The agent will plan → structure → format → export.
              </div>
            </div>
            <motion.button
              type="button"
              whileTap={{ scale: 0.98 }}
              disabled={busy}
              onClick={onGenerate}
              className="rounded-xl bg-neutral-900 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-neutral-800 disabled:opacity-60 dark:bg-white dark:text-neutral-950"
            >
              {busy ? 'Generating…' : 'Generate'}
            </motion.button>
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="mt-3 h-28 w-full resize-none rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-neutral-900 outline-none placeholder:text-neutral-500 focus:ring-2 focus:ring-sky-400/30 dark:text-neutral-100"
          />

          {error ? <div className="mt-2 text-xs text-rose-400">{error}</div> : null}
        </GlassCard>

        {/* Formatting */}
        <GlassCard>
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            Formatting instructions
          </div>
          <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
            Paste requirements like fonts, margins, spacing, heading rules.
          </div>
          <textarea
            value={formatting}
            onChange={(e) => setFormatting(e.target.value)}
            className="mt-3 h-28 w-full resize-none rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-neutral-900 outline-none placeholder:text-neutral-500 focus:ring-2 focus:ring-sky-400/30 dark:text-neutral-100"
          />

          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-neutral-700 dark:text-neutral-300">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeTitlePage}
                onChange={(e) => setIncludeTitlePage(e.target.checked)}
              />
              Title page
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeToc}
                onChange={(e) => setIncludeToc(e.target.checked)}
              />
              Table of contents
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeCharts}
                onChange={(e) => setIncludeCharts(e.target.checked)}
              />
              Embed charts
            </label>
          </div>
        </GlassCard>

        {/* Style */}
        <GlassCard>
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Style presets</div>
          <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
            Choose a preset. It applies fonts, spacing, margins, and heading styles.
          </div>
          <div className="mt-3">
            <StylePresets value={preset} onChange={setPreset} />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-neutral-700 dark:text-neutral-300">Tone:</span>
            {(['formal', 'simple', 'technical'] as Tone[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTone(t)}
                className={`rounded-xl border border-white/10 px-3 py-1 ${
                  tone === t
                    ? 'bg-neutral-900 text-white dark:bg-white dark:text-neutral-950'
                    : 'bg-white/10 text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </GlassCard>

        {/* Template upload */}
        <GlassCard>
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Template cloning</div>
          <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
            Upload a template document. DOCX templates are cloned with highest fidelity.
          </div>
          <div className="mt-3">
            <UploadDropzone onUpload={uploadTemplate} uploaded={template} />
          </div>
        </GlassCard>

        {/* Manual chart builder */}
        <GlassCard>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Manual charts
              </div>
              <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
                Add your own charts; they'll be embedded into DOCX/PDF exports.
              </div>
            </div>
            <button
              type="button"
              onClick={() =>
                setManualCharts((prev) => [
                  ...prev,
                  {
                    kind: newChartKind,
                    title: `Chart ${prev.length + 1}`,
                    labels: ['A', 'B', 'C'],
                    values: [10, 20, 30],
                    x_label: '',
                    y_label: 'Value',
                  },
                ])
              }
              className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
            >
              Add chart
            </button>
          </div>

          <div className="mt-3 flex items-center gap-2 text-xs text-neutral-700 dark:text-neutral-300">
            <span>Next type:</span>
            <select
              value={newChartKind}
              onChange={(e) => setNewChartKind(e.target.value as ChartKind)}
              className="rounded-xl border border-white/10 bg-white/10 px-2 py-1 text-xs text-neutral-900 outline-none dark:bg-white/5 dark:text-neutral-100"
            >
              <option value="bar">Bar</option>
              <option value="line">Line</option>
              <option value="pie">Pie</option>
            </select>
          </div>

          <div className="mt-3 space-y-2">
            <AnimatePresence>
              {manualCharts.map((c, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-neutral-700 dark:text-neutral-300"
                >
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-neutral-900 dark:text-neutral-100">
                      {c.title || `Chart ${idx + 1}`}
                    </div>
                    <button
                      type="button"
                      onClick={() => setManualCharts((prev) => prev.filter((_, i) => i !== idx))}
                      className="rounded-lg border border-white/10 bg-white/10 px-2 py-1 text-[11px] hover:bg-rose-500/10 hover:text-rose-500"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="mt-1">Type: {c.kind}</div>
                  <div className="mt-1">Labels: {c.labels.join(', ')}</div>
                  <div className="mt-1">Values: {c.values.join(', ')}</div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </GlassCard>
      </div>

      {/* ── Right column: output ──────────────────────────────────────────── */}
      <div className="space-y-4">
        {/* AI output + exports */}
        <GlassCard>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">AI output</div>
              <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
                Editable sections. Rewrite individual sections by tone.
              </div>
            </div>
            {documentId ? <ExportButtons documentId={documentId} /> : null}
          </div>

          {pipeline.length ? (
            <div className="mt-4">
              <PipelineSteps steps={pipeline} />
            </div>
          ) : (
            <div className="mt-4 text-xs text-neutral-700 dark:text-neutral-300">
              Generate a document to see the pipeline.
            </div>
          )}
        </GlassCard>

        {/* AI-suggested charts panel */}
        {(suggestedCharts.length > 0 || documentId) ? (
          <GlassCard>
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  AI-suggested charts
                </div>
                <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
                  Charts identified from your document's data. Preview, add to export, or download.
                </div>
              </div>
              {documentId ? (
                <button
                  type="button"
                  disabled={busyAnalyze}
                  onClick={onAnalyzeCharts}
                  className="shrink-0 rounded-xl border border-white/10 bg-violet-500/10 px-3 py-2 text-xs font-semibold text-violet-600 hover:bg-violet-500/20 disabled:opacity-60 dark:text-violet-400"
                >
                  {busyAnalyze ? 'Analyzing…' : suggestedCharts.length ? 'Re-analyze' : 'Analyze'}
                </button>
              ) : null}
            </div>

            {suggestedCharts.length === 0 && !busyAnalyze ? (
              <div className="mt-3 text-xs text-neutral-500 dark:text-neutral-400">
                {documentId
                  ? 'Click "Analyze" to have the AI identify charts suitable for your document.'
                  : 'Generate a document first, then run chart analysis.'}
              </div>
            ) : null}

            {busyAnalyze ? (
              <div className="mt-3 text-xs text-neutral-500 dark:text-neutral-400 animate-pulse">
                Analyzing document for data…
              </div>
            ) : null}

            <AnimatePresence>
              {suggestedCharts.length > 0 ? (
                <div className="mt-3 space-y-3">
                  {suggestedCharts.map((chart, idx) => (
                    <ChartCard
                      key={idx}
                      chart={chart}
                      index={idx + 1}
                      documentId={documentId}
                      isAdded={addedSuggested.has(idx)}
                      onAdd={() =>
                        setAddedSuggested((prev) => {
                          const next = new Set(prev)
                          next.add(idx)
                          return next
                        })
                      }
                      onRemove={() =>
                        setAddedSuggested((prev) => {
                          const next = new Set(prev)
                          next.delete(idx)
                          return next
                        })
                      }
                    />
                  ))}
                </div>
              ) : null}
            </AnimatePresence>
          </GlassCard>
        ) : null}

        {/* Preview + section editor */}
        <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
          <GlassCard className="2xl:col-span-1">
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Live preview</div>
            <div className="mt-3 h-[520px]">
              <PreviewPanel title={generated?.title || 'Preview'} sections={sections} />
            </div>
          </GlassCard>

          <GlassCard className="2xl:col-span-1">
            <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Edit sections</div>
            <div className="mt-3 space-y-3">
              {sections.length ? (
                sections.map((s) => (
                  <SectionEditor
                    key={s.id}
                    section={s}
                    onChange={(next) =>
                      setSections((prev) => prev.map((p) => (p.id === next.id ? next : p)))
                    }
                    onRewrite={(t) => void rewrite(s.id, t)}
                    busyTone={busyRewrite?.id === s.id ? busyRewrite.tone : null}
                  />
                ))
              ) : (
                <div className="text-xs text-neutral-700 dark:text-neutral-300">
                  No sections yet. Click Generate.
                </div>
              )}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
