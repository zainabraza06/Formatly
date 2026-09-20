import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { cn } from '../lib/cn'
import { docosApi } from '../lib/docosApi'
import {
  downloadBlob, isAbort, paperApi,
  type ComposeRequest, type Depth, type PaperSpec, type StyleSummary,
} from '../lib/paperApi'
import {
  outlineInstruction, replaceSection, sectionBlocksFrom, sectionRequest, sectionsOf,
  suggestedOutline, type Section,
} from '../lib/paperSections'
import { useRegisterCommands } from '../context/command-context'
import { useReportError } from '../hooks/useReportError'
import { explain } from '../lib/errors'
import {
  Button, Card, Field, Input, Select, Textarea, Tabs, useToast,
} from '../components/ui'
import {
  ChevronLeftIcon, ChevronRightIcon, ComposeIcon, DownloadIcon, EditorIcon, SparkIcon,
} from '../components/icons'
import { ExactPreview } from '../components/paper/ExactPreview'
import { GenerationStatus } from '../components/paper/GenerationStatus'
import { InstructionRefiner, RefineButton } from '../components/paper/InstructionRefiner'
import { OutlineEditor } from '../components/paper/OutlineEditor'
import { SectionReview } from '../components/paper/SectionReview'
import { Stepper, type Step } from '../components/paper/Stepper'
import { Appear, AppearGroup } from '../components/motion/Appear'

// A model left to itself writes concisely, so depth has to be asked for.
const DEPTH_OPTIONS: { id: Depth; label: string; hint: string }[] = [
  { id: 'brief', label: 'Brief', hint: '1–2 paragraphs per section' },
  { id: 'standard', label: 'Standard', hint: '2–3 paragraphs per section' },
]

// Suggestions only — the field is free text, so any document kind works.
const DOC_KINDS = [
  'paper', 'report', 'assignment', 'literature review', 'case study', 'proposal',
  'memo', 'white paper', 'technical documentation', 'essay', 'thesis chapter',
]

const CUSTOM_KIND = '__custom_kind__'

const BUILTIN_STYLES: StyleSummary[] = [
  { id: 'ieee', name: 'IEEE Conference (2-Column)', columns: '2', builtin: 'true', heading_scheme: 'roman_alpha', table_borders: 'horizontal' },
  { id: 'ieee_1col', name: 'IEEE Conference (1-Column)', columns: '1', builtin: 'true', heading_scheme: 'roman_alpha', table_borders: 'horizontal' },
  { id: 'assignment', name: 'Formal Assignment', columns: '1', builtin: 'true', heading_scheme: 'decimal', table_borders: 'grid' },
]

const STEPS: Step[] = [
  { id: 'material', label: 'Material', hint: 'What it should be about' },
  { id: 'structure', label: 'Structure', hint: 'Sections and style' },
  { id: 'generate', label: 'Generate', hint: 'Write the document' },
  { id: 'review', label: 'Review', hint: 'Read it and fix what you want' },
]

const DRAFT_KEY = 'formatly.compose.draft'

interface DraftForm {
  rawText: string
  instructions: string
  docKind: string
  depth: Depth
  style: string
  outline: string[]
  titleHint: string
  authorName: string
  authorAffil: string
}

const EMPTY_FORM: DraftForm = {
  rawText: '', instructions: '', docKind: 'paper', depth: 'standard',
  style: 'ieee', outline: [], titleHint: '', authorName: '', authorAffil: '',
}

/**
 * Generating a document, as four decisions rather than one long form.
 *
 * The form used to show everything at once — material, instructions, style,
 * kind, depth, title, author, affiliation — and then hand back a finished
 * document to accept or throw away whole. Here the structure is settled before
 * anything is written, and afterwards each section can be rewritten on its own.
 */
export function ComposePaper() {
  const navigate = useNavigate()
  const toast = useToast()
  const report = useReportError()

  const reduced = useReducedMotion()
  const [step, setStep] = useState(0)
  // Which way the last move went, so a step arrives from the side it came
  // from: forward slides in from the right, Back from the left.
  const [direction, setDirection] = useState(1)
  const [furthest, setFurthest] = useState(0)
  const [form, setForm] = useState<DraftForm>(() => loadDraft())
  const [styles, setStyles] = useState<StyleSummary[]>(BUILTIN_STYLES)
  const [refining, setRefining] = useState(false)
  const [showMaterialError, setShowMaterialError] = useState(false)

  const [spec, setSpec] = useState<PaperSpec | null>(null)
  const [provider, setProvider] = useState('')
  const [busy, setBusy] = useState<'idle' | 'generating' | 'rendering' | 'section' | 'handoff'>('idle')
  const [busySection, setBusySection] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<'exact' | 'reading'>('exact')

  const runRef = useRef<AbortController | null>(null)
  // Bumped whenever the spec changes, so the preview remounts and renders the
  // document that is on screen rather than the one before it.
  const [revision, setRevision] = useState(0)

  const set = <K extends keyof DraftForm>(key: K, value: DraftForm[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  // The form survives a reload: losing a page of pasted material to a stray
  // refresh is the kind of thing people do not come back from.
  useEffect(() => {
    const id = window.setTimeout(() => {
      try { localStorage.setItem(DRAFT_KEY, JSON.stringify(form)) } catch { /* private mode */ }
    }, 400)
    return () => window.clearTimeout(id)
  }, [form])

  useEffect(() => {
    paperApi.styles()
      .then((list) => { if (list.length) setStyles(list) })
      .catch(() => { /* the built-ins stay, rather than an empty dropdown */ })
  }, [])

  const sections = useMemo(() => sectionsOf(spec), [spec])
  const styleName = styles.find((s) => s.id === form.style)?.name || form.style
  const running = busy === 'generating'

  const buildRequest = (): ComposeRequest => ({
    raw_text: form.rawText,
    style: form.style,
    doc_kind: form.docKind,
    depth: form.depth,
    instructions: [form.instructions.trim() || null, outlineInstruction(form.outline)]
      .filter(Boolean).join('\n\n') || null,
    title_hint: form.titleHint.trim() || null,
    authors: form.authorName.trim()
      ? [{ name: form.authorName.trim(), affiliation: form.authorAffil.trim() }]
      : [],
  })

  // ── actions ───────────────────────────────────────────────────────────────

  const go = (next: number) => {
    if (next === 1 && !form.rawText.trim()) {
      setShowMaterialError(true)
      document.getElementById('compose-material')?.focus()
      return
    }
    setDirection(next >= step ? 1 : -1)
    setStep(next)
    setFurthest((f) => Math.max(f, next))
  }

  const stop = () => {
    runRef.current?.abort()
    runRef.current = null
    setBusy('idle')
    toast.info('Generation stopped', 'Nothing you typed was lost.')
  }

  const generate = async () => {
    if (!form.rawText.trim()) { go(0); setShowMaterialError(true); return }
    const run = new AbortController()
    runRef.current = run
    setBusy('generating')
    setError(null)
    setSpec(null)
    setStep(2)
    setFurthest((f) => Math.max(f, 2))

    try {
      const res = await paperApi.generate(buildRequest(), run.signal)
      setSpec(res.spec)
      setRevision((r) => r + 1)
      setProvider(res.provider)
      setStep(3)
      setFurthest(3)
      toast.success('Your document is ready', 'Read it through — any section can be rewritten on its own.')
    } catch (e) {
      if (!isAbort(e)) {
        const { title, detail } = explain(e, 'write the document')
        setError(`${title}. ${detail}`)
      }
    } finally {
      if (runRef.current === run) {
        runRef.current = null
        setBusy('idle')
      }
    }
  }

  const regenerateSection = async (section: Section, note: string) => {
    if (!spec) return
    const before = spec
    setBusy('section')
    setBusySection(section.heading)
    try {
      const res = await paperApi.generate(sectionRequest(buildRequest(), spec, section, note))
      const blocks = sectionBlocksFrom(res.spec, section.heading)
      setSpec(replaceSection(spec, section, blocks))
      setRevision((r) => r + 1)
      toast.toast({
        tone: 'success',
        title: `“${section.heading}” rewritten`,
        description: 'The rest of the document is untouched.',
        action: {
          label: 'Undo',
          onClick: () => {
            setSpec(before)
            setRevision((r) => r + 1)
            toast.info('Rewrite undone', `“${section.heading}” is back as it was.`)
          },
        },
      })
    } catch (e) {
      report(e, `rewrite “${section.heading}”`, () => void regenerateSection(section, note))
    } finally {
      setBusy('idle')
      setBusySection(null)
    }
  }

  const download = async () => {
    const run = new AbortController()
    runRef.current = run
    setBusy('rendering')
    const id = toast.loading('Preparing your DOCX…')
    try {
      const b = spec
        ? await paperApi.renderSpec(spec, undefined, run.signal)
        : await paperApi.compose(buildRequest(), run.signal)
      downloadBlob(b, `${(spec?.meta.title || form.titleHint || 'document').slice(0, 60)}.docx`)
      toast.toast({ id, tone: 'success', title: 'DOCX downloaded' })
    } catch (e) {
      toast.dismiss(id)
      report(e, 'prepare the DOCX', download)
    } finally {
      if (runRef.current === run) {
        runRef.current = null
        setBusy('idle')
      }
    }
  }

  // The spec goes across directly rather than as a rendered .docx: the file
  // format has no word for a listing, an equation or a chart, so routing
  // through one would hand the editor loose paragraphs and anonymous pictures.
  const openInEditor = async () => {
    if (!spec) return
    setBusy('handoff')
    try {
      const res = await docosApi.importSpec(spec, spec.meta.title || 'Document')
      navigate(`/app/editor?doc=${encodeURIComponent(res.document_id)}`)
    } catch (e) {
      report(e, 'open it in the editor', openInEditor)
    } finally {
      setBusy('idle')
    }
  }

  const startOver = () => {
    setSpec(null)
    setProvider('')
    setError(null)
    setForm(EMPTY_FORM)
    try { localStorage.removeItem(DRAFT_KEY) } catch { /* private mode */ }
    setStep(0)
    setFurthest(0)
  }

  useRegisterCommands(() => [
    { id: 'compose-generate', group: 'Generate', label: 'Generate the document',
      icon: <ComposeIcon />, disabled: running || !form.rawText.trim(), run: generate },
    { id: 'compose-download', group: 'Generate', label: 'Download as DOCX',
      icon: <DownloadIcon />, disabled: !spec, run: download },
    { id: 'compose-editor', group: 'Generate', label: 'Open in the editor',
      icon: <EditorIcon />, disabled: !spec, run: openInEditor },
    { id: 'compose-restart', group: 'Generate', label: 'Start a new document',
      run: startOver },
  ], [spec, running, form.rawText])

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl text-ink">Generate a document</h1>
          <p className="mt-1 text-sm text-muted">{STEPS[step].hint}</p>
        </div>
        {spec && (
          <Button variant="ghost" size="sm" onClick={startOver}>Start a new one</Button>
        )}
      </div>

      <Stepper steps={STEPS} current={step} furthest={furthest} onGo={go} />

      <AnimatePresence mode="wait" custom={direction} initial={false}>
        <motion.div
          key={step}
          custom={direction}
          initial={reduced ? { opacity: 0 } : { opacity: 0, x: direction * 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={reduced ? { opacity: 0 } : { opacity: 0, x: direction * -24 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
        >

      {/* ── 1. Material ──────────────────────────────────────────────────── */}
      {step === 0 && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <Card className="space-y-4">
            <Field
              label="Your material"
              required
              error={showMaterialError && !form.rawText.trim()
                ? 'Add something to work from — a brief, notes, data, or just a sentence saying what you need.'
                : null}
              hint="Everything goes here: what you want written, plus any notes, data, transcripts or code it should draw on. Numbers become tables and charts automatically."
            >
              {(props) => (
                <Textarea
                  {...props}
                  id="compose-material"
                  value={form.rawText}
                  onChange={(e) => { set('rawText', e.target.value); setShowMaterialError(false) }}
                  rows={16}
                  placeholder={`Say what you need, then paste everything it should be based on. For example:

Write a report on our Q3 customer churn for the leadership team.

Survey: 412 cancelling customers. Price 63%, missing features 21%, support 11%, other 5%.
Churn by month: July 4.2%, August 5.1%, September 6.8%.
Interview: "The renewal price jumped 40% with no warning."`}
                />
              )}
            </Field>

            <div>
              <div className="mb-1.5 flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-ink">Extra instructions</span>
                <RefineButton
                  disabled={!form.instructions.trim()}
                  active={refining}
                  onClick={() => setRefining((r) => !r)}
                />
              </div>
              <Textarea
                value={form.instructions}
                onChange={(e) => set('instructions', e.target.value)}
                rows={3}
                aria-label="Extra instructions"
                placeholder={`e.g. Bold the important keywords and technical terms.
Keep it under 4 pages.
Write in the first person plural.`}
              />
              <p className="mt-1.5 text-xs text-faint">
                Followed as written, and they override the defaults. One per line is fine.
              </p>

              {refining && form.instructions.trim() && (
                <InstructionRefiner
                  instructions={form.instructions}
                  rawText={form.rawText}
                  docKind={form.docKind}
                  style={form.style}
                  onAccept={(improved) => { set('instructions', improved); setRefining(false) }}
                  onClose={() => setRefining(false)}
                />
              )}
            </div>
          </Card>

          <div className="space-y-4">
            <Card className="space-y-4">
              <Field label="Document kind">
                {(props) => (
                  <>
                    <Select
                      {...props}
                      value={DOC_KINDS.includes(form.docKind) ? form.docKind : CUSTOM_KIND}
                      onChange={(e) => set('docKind', e.target.value === CUSTOM_KIND ? '' : e.target.value)}
                    >
                      {DOC_KINDS.map((k) => (
                        <option key={k} value={k}>{k.charAt(0).toUpperCase() + k.slice(1)}</option>
                      ))}
                      <option value={CUSTOM_KIND}>Something else…</option>
                    </Select>
                    {!DOC_KINDS.includes(form.docKind) && (
                      <Input
                        value={form.docKind}
                        onChange={(e) => set('docKind', e.target.value)}
                        placeholder="e.g. grant proposal, policy brief"
                        aria-label="Document kind"
                        className="mt-2"
                      />
                    )}
                  </>
                )}
              </Field>

              <div>
                <p className="mb-1.5 text-sm font-medium text-ink">Depth</p>
                <Tabs
                  label="How much to write per section"
                  value={form.depth}
                  onChange={(id) => set('depth', id)}
                  items={DEPTH_OPTIONS.map((d) => ({ id: d.id, label: d.label }))}
                  className="w-full"
                />
                <p className="mt-1.5 text-xs text-faint">
                  {DEPTH_OPTIONS.find((d) => d.id === form.depth)?.hint}
                </p>
              </div>
            </Card>

            <div className="flex justify-end">
              <Button variant="primary" onClick={() => go(1)} trailingIcon={<ChevronRightIcon />}>
                Continue
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── 2. Structure ─────────────────────────────────────────────────── */}
      {step === 1 && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <Card className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-ink">Sections</h2>
              <p className="mt-0.5 text-sm text-muted">
                Decide the structure now, and the writer follows it exactly.
              </p>
            </div>
            <OutlineEditor
              sections={form.outline}
              onChange={(next) => set('outline', next)}
              suggestion={suggestedOutline(form.docKind)}
            />
          </Card>

          <div className="space-y-4">
            <Card className="space-y-4">
              <Field label="Style" hint={`Rendered as ${styleName}.`}>
                {(props) => (
                  <Select {...props} value={form.style} onChange={(e) => set('style', e.target.value)}>
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
                  </Select>
                )}
              </Field>

              <Field label="Title" optional hint="Leave blank to let the AI title it.">
                {(props) => (
                  <Input
                    {...props}
                    value={form.titleHint}
                    onChange={(e) => set('titleHint', e.target.value)}
                    placeholder="Untitled"
                  />
                )}
              </Field>

              <div className="grid grid-cols-2 gap-3">
                <Field label="Author" optional>
                  {(props) => (
                    <Input {...props} value={form.authorName}
                           onChange={(e) => set('authorName', e.target.value)} placeholder="Your name" />
                  )}
                </Field>
                <Field label="Affiliation" optional>
                  {(props) => (
                    <Input {...props} value={form.authorAffil}
                           onChange={(e) => set('authorAffil', e.target.value)} placeholder="Organisation" />
                  )}
                </Field>
              </div>
            </Card>

            <div className="flex justify-between gap-2">
              <Button variant="ghost" onClick={() => go(0)} leadingIcon={<ChevronLeftIcon />}>
                Back
              </Button>
              <Button variant="primary" onClick={() => go(2)} trailingIcon={<ChevronRightIcon />}>
                Continue
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── 3. Generate ──────────────────────────────────────────────────── */}
      {step === 2 && (
        <div className="mx-auto w-full max-w-2xl space-y-4">
          <Card className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-ink">Ready to write</h2>
              <p className="mt-0.5 text-sm text-muted">
                This is what the document will be made from. Anything here can still be changed.
              </p>
            </div>

            <AppearGroup className="divide-y divide-line rounded-md border border-line" stagger={0.04}>
              <Summary label="Material" value={`${words(form.rawText)} words of material`} onEdit={() => go(0)} />
              <Summary
                label="Structure"
                value={form.outline.length ? form.outline.join(' · ') : 'Planned by the AI'}
                onEdit={() => go(1)}
              />
              <Summary label="Style" value={styleName} onEdit={() => go(1)} />
              <Summary label="Kind & depth" value={`${form.docKind || 'document'} · ${form.depth}`} onEdit={() => go(0)} />
              {form.instructions.trim() ? (
                <Summary label="Instructions" value={form.instructions.trim()} onEdit={() => go(0)} />
              ) : <></>}
            </AppearGroup>

            {!running && (
              <Button variant="primary" size="lg" fullWidth onClick={generate} leadingIcon={<SparkIcon />}>
                {spec ? 'Write it again' : 'Write the document'}
              </Button>
            )}
          </Card>

          <GenerationStatus
            state={running ? 'working' : error ? 'error' : null}
            error={error}
            onRetry={generate}
            onStop={stop}
          />

          {!running && !error && (
            <div className="flex justify-start">
              <Button variant="ghost" onClick={() => go(1)} leadingIcon={<ChevronLeftIcon />}>Back</Button>
            </div>
          )}
        </div>
      )}

      {/* ── 4. Review ────────────────────────────────────────────────────── */}
      {step === 3 && spec && (
        <Appear className="space-y-4">
          <Card className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-ink">
                {spec.meta.title || 'Untitled document'}
              </h2>
              <p className="mt-0.5 text-xs text-muted">
                {styleName}
                {provider && <> · written by {provider}</>}
                {' · '}{sections.length} {sections.length === 1 ? 'section' : 'sections'}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={openInEditor}
                loading={busy === 'handoff'}
                leadingIcon={<EditorIcon />}
              >
                Edit in the editor
              </Button>
              <Button
                variant="primary"
                onClick={download}
                loading={busy === 'rendering'}
                leadingIcon={<DownloadIcon />}
              >
                Download DOCX
              </Button>
            </div>
          </Card>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Tabs
                  label="How to show the document"
                  size="sm"
                  value={preview}
                  onChange={setPreview}
                  items={[
                    { id: 'exact', label: 'Exact page' },
                    { id: 'reading', label: 'Reading view' },
                  ]}
                />
                <p className="text-2xs text-faint">
                  {preview === 'exact'
                    ? 'This is the file you will download.'
                    : 'A plain reading view — quicker, but not the exact layout.'}
                </p>
              </div>

              <ExactPreview key={`${revision}-${preview}`} spec={spec} mode={preview} />
            </div>

            <div className="space-y-2">
              <div>
                <h2 className="text-base font-semibold text-ink">Sections</h2>
                <p className="mt-0.5 text-sm text-muted">
                  Rewrite any one of them without touching the rest.
                </p>
              </div>
              <SectionReview
                sections={sections}
                busyHeading={busySection}
                disabled={busy !== 'idle'}
                onRegenerate={regenerateSection}
              />
            </div>
          </div>
        </Appear>
      )}

        </motion.div>
      </AnimatePresence>

      {/* The review step with nothing to review: only reachable by jumping
          back to it after starting over. */}
      {step === 3 && !spec && (
        <Card>
          <p className="text-sm text-muted">
            Nothing has been written yet.{' '}
            <button onClick={() => go(2)} className="font-medium text-brand-ink hover:underline">
              Go back and generate the document
            </button>
            .
          </p>
        </Card>
      )}
    </div>
  )
}

function Summary({ label, value, onEdit }: { label: string; value: string; onEdit: () => void }) {
  return (
    <div className="flex items-start gap-3 px-3 py-2.5">
      <dt className="w-28 shrink-0 text-xs font-medium text-muted">{label}</dt>
      <dd className={cn('min-w-0 flex-1 text-sm text-ink', 'line-clamp-2')}>{value}</dd>
      <button
        type="button"
        onClick={onEdit}
        className="shrink-0 text-xs font-medium text-brand-ink hover:underline"
      >
        Change
      </button>
    </div>
  )
}

function words(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length
}

function loadDraft(): DraftForm {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return EMPTY_FORM
    const parsed = JSON.parse(raw) as Partial<DraftForm>
    return { ...EMPTY_FORM, ...parsed, outline: Array.isArray(parsed.outline) ? parsed.outline : [] }
  } catch {
    return EMPTY_FORM
  }
}
