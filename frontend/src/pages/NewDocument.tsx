import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
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

function toDraft(r: GenerateResponse, req: GenerateRequest, template?: TemplateAnalyzeResponse | null): Draft {
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
  }
}

export function NewDocument() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT)
  const [formatting, setFormatting] = useState(DEFAULT_FORMAT)
  const [preset, setPreset] = useState<StylePreset>('business')
  const [tone, setTone] = useState<Tone>('formal')

  const [includeTitlePage, setIncludeTitlePage] = useState(true)
  const [includeToc, setIncludeToc] = useState(true)
  const [includeCharts, setIncludeCharts] = useState(true)

  const [template, setTemplate] = useState<TemplateAnalyzeResponse | null>(null)

  const [charts, setCharts] = useState<ChartSpec[]>([
    { kind: 'bar', title: 'Example Chart', labels: ['A', 'B', 'C'], values: [30, 45, 25] },
  ])
  const [newChartKind, setNewChartKind] = useState<ChartKind>('bar')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [generated, setGenerated] = useState<GenerateResponse | null>(null)
  const [pipeline, setPipeline] = useState<GenerateResponse['pipeline']>([])
  const [sections, setSections] = useState<DocumentSection[]>([])

  const [busyRewrite, setBusyRewrite] = useState<{ id: string; tone: Tone } | null>(null)

  const documentId = generated?.document_id

  const exportLinks = useMemo(() => {
    if (!documentId) return null
    return {
      docx: api.exportDocxUrl(documentId),
      pdf: api.exportPdfUrl(documentId),
    }
  }, [documentId])

  const autosaveTimer = useRef<number | null>(null)

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
    }

    if (autosaveTimer.current) window.clearTimeout(autosaveTimer.current)
    autosaveTimer.current = window.setTimeout(() => {
      api.saveDraft(documentId, draft).catch(() => {
        // keep silent; UI remains usable even if autosave fails
      })
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
  ])

  async function onGenerate() {
    setError(null)
    setBusy(true)
    try {
      const req: GenerateRequest = {
        prompt,
        formatting_instructions: formatting,
        style_preset: preset,
        tone,
        include_title_page: includeTitlePage,
        include_toc: includeToc,
        include_charts: includeCharts,
        charts: includeCharts ? charts : [],
        template_id: template?.template_id || null,
      }
      const r = await api.generate(req)
      setGenerated(r)
      setPipeline(r.pipeline)
      setSections(r.sections)

      const draft = toDraft(r, req, template)
      await api.saveDraft(r.document_id, draft)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed')
    } finally {
      setBusy(false)
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
      setSections((prev) => prev.map((s) => (s.id === sectionId ? { ...s, content: res.section.content } : s)))
    } finally {
      setBusyRewrite(null)
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <div className="space-y-4">
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
              <input type="checkbox" checked={includeToc} onChange={(e) => setIncludeToc(e.target.checked)} />
              Table of contents
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={includeCharts}
                onChange={(e) => setIncludeCharts(e.target.checked)}
              />
              Charts
            </label>
          </div>
        </GlassCard>

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

        <GlassCard>
          <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Template cloning</div>
          <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
            Upload a template document. DOCX templates are cloned with highest fidelity.
          </div>
          <div className="mt-3">
            <UploadDropzone onUpload={uploadTemplate} uploaded={template} />
          </div>
        </GlassCard>

        <GlassCard>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Chart generation</div>
              <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
                Add charts manually; they’ll be embedded into DOCX/PDF exports.
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                setCharts((prev) => [
                  ...prev,
                  {
                    kind: newChartKind,
                    title: `Chart ${prev.length + 1}`,
                    labels: ['A', 'B', 'C'],
                    values: [10, 20, 30],
                  },
                ])
              }}
              className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
            >
              Add chart
            </button>
          </div>

          <div className="mt-3 flex items-center gap-2 text-xs text-neutral-700 dark:text-neutral-300">
            <span>Next chart type:</span>
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
            {charts.map((c, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-neutral-700 dark:text-neutral-300"
              >
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-neutral-900 dark:text-neutral-100">
                    {c.title || `Chart ${idx + 1}`}
                  </div>
                  <button
                    type="button"
                    onClick={() => setCharts((prev) => prev.filter((_, i) => i !== idx))}
                    className="rounded-lg border border-white/10 bg-white/10 px-2 py-1 text-[11px] text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
                  >
                    Remove
                  </button>
                </div>
                <div className="mt-1">Type: {c.kind}</div>
                <div className="mt-1">Labels: {c.labels.join(', ')}</div>
                <div className="mt-1">Values: {c.values.join(', ')}</div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="space-y-4">
        <GlassCard>
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">AI output</div>
              <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
                Editable sections. Rewrite individual sections by tone.
              </div>
            </div>
            {exportLinks ? (
              <div className="flex gap-2">
                <a
                  href={exportLinks.docx}
                  className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold text-neutral-900 hover:bg-white/15 dark:bg-white/5 dark:text-neutral-100"
                >
                  Download DOCX
                </a>
                <a
                  href={exportLinks.pdf}
                  className="rounded-xl bg-neutral-900 px-3 py-2 text-xs font-semibold text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-950"
                >
                  Download PDF
                </a>
              </div>
            ) : null}
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
                    onChange={(next) => setSections((prev) => prev.map((p) => (p.id === next.id ? next : p)))}
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
