import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '../lib/cn'
import { applyTheme, getInitialTheme } from '../lib/theme'
import { Badge, Button, ButtonLink } from '../components/ui'
import { Logo } from '../components/Logo'
import { ProductMock } from '../components/landing/ProductMock'
import {
  CheckIcon, ChevronDownIcon, ComposeIcon, DocumentsIcon, DownloadIcon, EditorIcon,
  LayersIcon, MoonIcon, SparkIcon, SunIcon,
} from '../components/icons'

const STEPS = [
  {
    title: 'Bring what you have',
    body: 'Paste a brief, your notes, a table of numbers — or upload a Word document you already wrote.',
    icon: <DocumentsIcon className="h-5 w-5" />,
  },
  {
    title: 'Say what it should be',
    body: 'Fix the sections before a word is written, pick a style, and add any rule it must follow.',
    icon: <ComposeIcon className="h-5 w-5" />,
  },
  {
    title: 'Read it, fix it, export it',
    body: 'Rewrite any section on its own, tell the editor what to change in plain English, then download the DOCX or PDF.',
    icon: <DownloadIcon className="h-5 w-5" />,
  },
]

const FEATURES = [
  {
    title: 'Plain-English formatting',
    body: '“Make all headings consistent.” “Reformat the citations.” The editor works on the document’s real structure, not a find-and-replace.',
    icon: <EditorIcon className="h-5 w-5" />,
  },
  {
    title: 'Every change is reversible',
    body: 'Each instruction is a version. See exactly what changed, keep it, or undo it — nothing the AI does is final until you say so.',
    icon: <LayersIcon className="h-5 w-5" />,
  },
  {
    title: 'Rewrite one section',
    body: 'A weak conclusion does not mean regenerating the document. Rewrite that section alone and leave the rest untouched.',
    icon: <SparkIcon className="h-5 w-5" />,
  },
  {
    title: 'Real document styles',
    body: 'IEEE two-column, formal assignment, or your own stylesheet — applied to headings, tables, figures and captions alike.',
    icon: <DocumentsIcon className="h-5 w-5" />,
  },
  {
    title: 'Tables, charts and equations',
    body: 'Numbers in your material become tables and charts. LaTeX becomes mathematics. Both survive the export.',
    icon: <ComposeIcon className="h-5 w-5" />,
  },
  {
    title: 'Exports that hold together',
    body: 'DOCX and PDF from the same render, with the page preview shown before you save — so the file is what you saw.',
    icon: <DownloadIcon className="h-5 w-5" />,
  },
]

const PLANS = [
  {
    name: 'Free',
    price: 'Free',
    cadence: 'while in beta',
    blurb: 'Everything, for anyone with a document to write.',
    features: [
      'Generate documents from your own material',
      'Edit Word documents with AI instructions',
      'Full version history, undo and diffs',
      'DOCX and PDF export',
    ],
    cta: 'Start writing',
    highlighted: true,
  },
  {
    name: 'Team',
    price: 'Planned',
    cadence: '',
    blurb: 'Shared libraries and house styles for a group.',
    features: [
      'Everything in Free',
      'Shared document library',
      'Your organisation’s stylesheet',
      'Comments and review',
    ],
    cta: 'Start writing',
    highlighted: false,
  },
  {
    name: 'Institution',
    price: 'Planned',
    cadence: '',
    blurb: 'For departments with a style guide to enforce.',
    features: [
      'Everything in Team',
      'Enforced submission templates',
      'Single sign-on',
      'Self-hosted deployment',
    ],
    cta: 'Start writing',
    highlighted: false,
  },
]

const FAQS = [
  {
    q: 'Does it change my document without asking?',
    a: 'It applies what you asked for, then shows you what it did. Every instruction becomes a version, the change is named as it lands with Keep and Undo beside it, and you can compare any two versions word by word. Nothing is lost, and nothing is hidden.',
  },
  {
    q: 'What happens to my formatting when I upload a .docx?',
    a: 'The document is read into a structure that knows what a heading, a table, a figure and an equation are — not a wall of text. That is what lets an instruction like “make all headings consistent” find the headings, and what lets the export come back out as a real Word document.',
  },
  {
    q: 'Can I control the structure, or does the AI decide?',
    a: 'Either. List the sections yourself and the writer follows them exactly; leave the outline empty and it plans its own, and tells you what it chose.',
  },
  {
    q: 'What if one section is wrong but the rest is fine?',
    a: 'Rewrite that section on its own, optionally saying what should change about it. The other sections are not touched, and the rewrite can be undone.',
  },
  {
    q: 'Which formats can I export?',
    a: 'DOCX and PDF, from the same render, with a preview of the page before you save. PDF export needs LibreOffice on the server; where it is unavailable the app says so rather than failing quietly.',
  },
  {
    q: 'Is my work private?',
    a: 'Your documents belong to your account and are only listed and exported for you. Text you submit is sent to the language model that writes or edits it, so treat it as you would any hosted AI tool.',
  },
]

/**
 * The public page. Its job is to say what the product does, show it, and get
 * out of the way — so the first thing below the headline is the editor itself
 * rather than a stock illustration.
 */
export function LandingPage() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => getInitialTheme())

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return (
    <div className="min-h-screen bg-canvas">
      <a href="#main" className="skip-link rounded-md bg-brand px-3 py-2 text-sm font-medium text-brand-fg shadow-lg">
        Skip to content
      </a>

      {/* ── Nav ──────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-line bg-canvas/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <Logo to="/" />

          <nav aria-label="Sections" className="ml-4 hidden items-center gap-1 md:flex">
            {[
              ['How it works', '#how'],
              ['Features', '#features'],
              ['Pricing', '#pricing'],
              ['FAQ', '#faq'],
            ].map(([label, href]) => (
              <a
                key={href}
                href={href}
                className="rounded-md px-2.5 py-1.5 text-sm text-muted transition-colors duration-fast hover:bg-surface-2 hover:text-ink"
              >
                {label}
              </a>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost" size="md" iconOnly
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              leadingIcon={theme === 'dark' ? <SunIcon /> : <MoonIcon />}
            />
            <ButtonLink to="/login" variant="ghost" className="hidden sm:inline-flex">
              Log in
            </ButtonLink>
            <ButtonLink to="/app/compose" variant="primary">
              Get started
            </ButtonLink>
          </div>
        </div>
      </header>

      <main id="main">
        {/* ── Hero ───────────────────────────────────────────────────────── */}
        <section className="relative overflow-hidden">
          {/* Decoration, behind everything and announced to nobody. */}
          <div className="hero-wash pointer-events-none absolute inset-x-0 top-0 h-[42rem]" aria-hidden />
          <div className="hero-grid pointer-events-none absolute inset-x-0 top-0 h-[42rem]" aria-hidden />

          <div className="relative mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24">
            <div className="mx-auto max-w-3xl text-center">
              <Badge tone="brand" icon={<SparkIcon className="h-3.5 w-3.5" />}>
                AI that formats, not just writes
              </Badge>

              <h1 className="mt-6 text-5xl text-ink sm:text-6xl">
                Documents that come out{' '}
                <span className="bg-gradient-to-br from-brand to-info bg-clip-text text-transparent">
                  properly formatted
                </span>
              </h1>

              <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-muted">
                Write a paper from your own material, or bring a Word document and tell it
                what to fix in plain English. Every change is shown, versioned, and
                reversible.
              </p>

              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <ButtonLink to="/app/compose" variant="primary" size="lg">
                  Write a document
                </ButtonLink>
                <ButtonLink to="/app" variant="secondary" size="lg" leadingIcon={<EditorIcon />}>
                  Edit one I have
                </ButtonLink>
              </div>

              <p className="mt-4 text-xs text-faint">Free while in beta · no card, no credits</p>
            </div>

            {/* The product, at the size you can actually read it. */}
            <div className="relative mx-auto mt-16 max-w-5xl">
              <ProductMock className="hero-frame !border-0" />
            </div>

            {/* What it knows how to produce — capabilities, not customer logos
                we do not have. */}
            <div className="mt-14 flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
              <span className="text-2xs font-medium uppercase tracking-wide text-faint">
                Formats it writes
              </span>
              {['IEEE two-column', 'Formal assignment', 'Reports', 'Proposals', 'Thesis chapters', 'Your own stylesheet']
                .map((label) => (
                  <span key={label} className="text-sm text-muted">{label}</span>
                ))}
            </div>
          </div>
        </section>

        {/* ── How it works ───────────────────────────────────────────────── */}
        <Section id="how" title="Three steps, start to finish"
                 lede="No template to pick, no settings to learn first.">
          <ol className="grid gap-4 md:grid-cols-3">
            {STEPS.map((step, i) => (
              <li key={step.title} className="rounded-lg border border-line bg-surface p-6">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-soft text-brand-ink" aria-hidden>
                    {step.icon}
                  </span>
                  <span className="text-2xs font-medium uppercase tracking-wide text-faint">
                    Step {i + 1}
                  </span>
                </div>
                <h3 className="mt-5 text-lg text-ink">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </Section>

        {/* ── Features ───────────────────────────────────────────────────── */}
        <Section id="features" tinted title="What it actually does"
                 lede="The parts that matter when a document has to be handed in, not just drafted.">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="group rounded-lg border border-line bg-surface p-6 transition-[border-color,box-shadow,transform] duration-slow ease-out hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md"
              >
                <span
                  className="flex h-9 w-9 items-center justify-center rounded-md border border-brand/15 bg-brand-soft text-brand-ink transition-colors duration-fast group-hover:border-brand/30"
                  aria-hidden
                >
                  {f.icon}
                </span>
                <h3 className="mt-5 text-lg text-ink">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{f.body}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* ── Pricing ────────────────────────────────────────────────────── */}
        <Section id="pricing" title="Pricing"
                 lede="Formatly is in beta and everything in it is free. The paid tiers below are what is planned, not what is charged — there is no billing to sign up to yet.">
          <div className="grid gap-4 lg:grid-cols-3">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={cn(
                  'flex flex-col rounded-lg border bg-surface p-6',
                  // The available plan is marked by its border, not by a
                  // shadow: one of three cards lifting off the page for no
                  // functional reason is decoration.
                  plan.highlighted ? 'border-brand' : 'border-line',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-lg text-ink">{plan.name}</h3>
                  {plan.highlighted ? (
                    <Badge tone="brand">Available now</Badge>
                  ) : (
                    <Badge>Not yet available</Badge>
                  )}
                </div>

                <p className="mt-5 flex items-baseline gap-1.5">
                  <span className={cn(plan.highlighted ? 'text-3xl text-ink' : 'text-lg text-muted')}>
                    {plan.price}
                  </span>
                  {plan.cadence && <span className="text-sm text-faint">{plan.cadence}</span>}
                </p>
                <p className="mt-2 text-sm text-muted">{plan.blurb}</p>

                <ul className="mt-5 flex-1 space-y-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex gap-2 text-sm text-muted">
                      <CheckIcon
                        className={cn('mt-0.5 h-4 w-4 shrink-0', plan.highlighted ? 'text-brand-ink' : 'text-faint')}
                      />
                      {f}
                    </li>
                  ))}
                </ul>

                <ButtonLink
                  to="/app/compose"
                  variant={plan.highlighted ? 'primary' : 'secondary'}
                  fullWidth
                  className="mt-6"
                >
                  {plan.cta}
                </ButtonLink>
              </div>
            ))}
          </div>
        </Section>

        {/* ── FAQ ────────────────────────────────────────────────────────── */}
        <Section id="faq" tinted title="Questions" lede="The ones worth answering before you sign up.">
          <div className="mx-auto max-w-2xl divide-y divide-line overflow-hidden rounded-lg border border-line bg-surface">
            {FAQS.map((item) => (
              <details key={item.q} className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-base font-medium text-ink transition-colors duration-fast hover:bg-surface-2">
                  {item.q}
                  <ChevronDownIcon className="h-4 w-4 shrink-0 text-faint transition-transform duration-fast group-open:rotate-180" />
                </summary>
                <p className="px-5 pb-5 text-sm leading-relaxed text-muted">{item.a}</p>
              </details>
            ))}
          </div>
        </Section>

        {/* ── Closing CTA ────────────────────────────────────────────────── */}
        <section className="mx-auto max-w-6xl px-4 pb-24 pt-16 sm:px-6 sm:pt-24">
          <div className="relative overflow-hidden rounded-xl bg-accent px-6 py-16 text-center">
            <div
              className="pointer-events-none absolute inset-0 opacity-90"
              style={{
                background:
                  'radial-gradient(40rem 20rem at 50% -20%, rgb(var(--brand) / 0.55), transparent 70%)',
              }}
              aria-hidden
            />
            <div className="relative">
              <h2 className="text-2xl text-accent-fg sm:text-3xl">Have something due?</h2>
              <p className="mx-auto mt-3 max-w-md text-md leading-relaxed text-accent-fg/70">
                Paste what you have. You will have a formatted document, and a way to fix
                anything in it, in a couple of minutes.
              </p>
              <ButtonLink
                to="/app/compose"
                size="lg"
                className="mt-7 bg-surface text-ink hover:bg-surface-2"
              >
                Write a document
              </ButtonLink>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-xs text-muted sm:px-6">
          <div className="flex items-center gap-2">
            <Logo to={null} compact />
            <span>© {new Date().getFullYear()} Formatly</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/login" className="rounded-sm hover:text-ink">Log in</Link>
            <a href="#faq" className="rounded-sm hover:text-ink">FAQ</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

function Section({
  id, title, lede, children, tinted,
}: { id: string; title: string; lede: string; children: ReactNode; tinted?: boolean }) {
  return (
    <section
      id={id}
      className={cn(
        'scroll-mt-14 border-t border-line py-16 sm:py-24',
        // Alternating surfaces give the page a rhythm. Four identical bands of
        // white cards on white is what makes a marketing page read as a
        // template.
        tinted && 'bg-surface-2/40',
      )}
    >
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mx-auto mb-10 max-w-2xl text-center sm:mb-12">
          <h2 className="text-2xl text-ink sm:text-3xl">{title}</h2>
          <p className="mt-3 text-md leading-relaxed text-muted">{lede}</p>
        </div>
        {children}
      </div>
    </section>
  )
}
