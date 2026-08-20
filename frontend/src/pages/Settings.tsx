import { useEffect, useState } from 'react'
import { GlassCard } from '../components/GlassCard'
import { API_BASE_URL, api } from '../lib/api'
import { authApi, getToken, type AuthUser } from '../lib/auth'
import { paperApi, type StyleSummary } from '../lib/paperApi'

type Health = { status: string; version: string; exact_preview: boolean }
type Providers = Record<string, { state: string; model: string; has_key: boolean }>

/** Settings reports what the system is actually doing, so nothing has to be
 *  inferred from a failure later: which backend is answering, whether the model
 *  is reachable, and which optional capabilities are present on this machine. */
export function Settings() {
  const [health, setHealth] = useState<Health | null>(null)
  const [providers, setProviders] = useState<Providers | null>(null)
  const [styles, setStyles] = useState<StyleSummary[]>([])
  const [user, setUser] = useState<AuthUser | null>(null)
  const [checkedAt, setCheckedAt] = useState<Date | null>(null)
  const [busy, setBusy] = useState(false)

  const refresh = () => {
    setBusy(true)
    const token = getToken()
    Promise.allSettled([
      api.health(),
      api.providerStatus(),
      paperApi.styles(),
      token ? authApi.me(token) : Promise.resolve(null),
    ]).then(([h, p, s, u]) => {
      setHealth(h.status === 'fulfilled' ? h.value : null)
      setProviders(p.status === 'fulfilled' ? p.value : null)
      setStyles(s.status === 'fulfilled' ? s.value : [])
      setUser(u.status === 'fulfilled' ? (u.value as AuthUser | null) : null)
      setCheckedAt(new Date())
      setBusy(false)
    })
  }
  useEffect(refresh, [])

  const reachable = health?.status === 'ok'

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">Settings</h1>
          <p className="mt-0.5 text-sm text-muted">
            Configuration and status for this installation.
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={busy}
          className="rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-2 disabled:opacity-50"
        >
          {busy ? 'Checking…' : 'Re-check'}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {/* ── service status ── */}
        <GlassCard>
          <SectionTitle>Service status</SectionTitle>
          <dl className="mt-3 space-y-2.5">
            <Row label="Backend">
              <StatusDot ok={reachable} />
              <span className="ml-1.5">
                {reachable ? 'Reachable' : 'Not reachable'}
                {health?.version && (
                  <span className="text-faint"> · v{health.version}</span>
                )}
              </span>
            </Row>
            <Row label="API endpoint">
              <Mono>{API_BASE_URL}</Mono>
            </Row>
            <Row label="Exact preview">
              <StatusDot ok={!!health?.exact_preview} />
              <span className="ml-1.5">
                {health?.exact_preview ? 'Available' : 'Unavailable'}
              </span>
            </Row>
            {checkedAt && (
              <Row label="Last checked">
                <span className="text-faint">{checkedAt.toLocaleTimeString()}</span>
              </Row>
            )}
          </dl>
          {health && !health.exact_preview && (
            <Note>
              LibreOffice was not found, so the composer falls back to a reading
              view instead of rendering the real document. Downloads are unaffected.
            </Note>
          )}
        </GlassCard>

        {/* ── model ── */}
        <GlassCard>
          <SectionTitle>Language model</SectionTitle>
          {providers && Object.keys(providers).length > 0 ? (
            <dl className="mt-3 space-y-2.5">
              {Object.entries(providers).map(([name, p]) => (
                <div key={name} className="space-y-2.5">
                  <Row label="Provider">
                    <StatusDot ok={p.state === 'ready'} />
                    <span className="ml-1.5 capitalize">{name}</span>
                    <span className="text-faint"> · {p.state}</span>
                  </Row>
                  <Row label="Model">
                    <Mono>{p.model}</Mono>
                  </Row>
                  <Row label="API key">
                    <StatusDot ok={p.has_key} />
                    <span className="ml-1.5">{p.has_key ? 'Configured' : 'Missing'}</span>
                  </Row>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-3 text-xs text-muted">Provider status unavailable.</p>
          )}
          {providers && Object.values(providers).some((p) => !p.has_key) && (
            <Note>
              Set <Mono>MISTRAL_API_KEY</Mono> in the backend&apos;s{' '}
              <Mono>.env</Mono> and restart it. Keys are issued at
              console.mistral.ai.
            </Note>
          )}
        </GlassCard>

        {/* ── document styles ── */}
        <GlassCard>
          <SectionTitle>Document styles</SectionTitle>
          {styles.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {styles.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface-2 px-3 py-2"
                >
                  <span className="text-xs font-medium text-ink">{s.name}</span>
                  <span className="shrink-0 text-[10px] text-faint">
                    <Mono>{s.id}</Mono> · {s.columns} col ·{' '}
                    {s.heading_scheme.replace(/_/g, ' ')}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-xs text-muted">No styles returned.</p>
          )}
        </GlassCard>

        {/* ── capabilities ── */}
        <GlassCard>
          <SectionTitle>Document capabilities</SectionTitle>
          <ul className="mt-3 space-y-1.5">
            {[
              'Charts generated from figures in your material',
              'Tables with style-appropriate rules and numbered captions',
              'Equations typeset from TeX markup, no LaTeX installation needed',
              'Code listings as text, or as an editor screenshot',
              'Program output as a console screenshot',
              'Cover sheet and page breaks on request',
              'Export to .docx, with an exact PDF preview',
            ].map((c) => (
              <li key={c} className="flex gap-2 text-xs leading-relaxed text-muted">
                <span className="mt-[3px] text-ink">·</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </GlassCard>

        {/* ── account ── */}
        <GlassCard>
          <SectionTitle>Account</SectionTitle>
          {user ? (
            <dl className="mt-3 space-y-2.5">
              <Row label="Name">{user.name || '—'}</Row>
              <Row label="Email">
                <Mono>{user.email}</Mono>
              </Row>
              <Row label="Member since">
                {new Date(user.created_at).toLocaleDateString()}
              </Row>
            </dl>
          ) : (
            <p className="mt-3 text-xs text-muted">Not signed in.</p>
          )}
        </GlassCard>

        {/* ── configuration reference ── */}
        <GlassCard>
          <SectionTitle>Configuration</SectionTitle>
          <p className="mt-1 text-[11px] text-muted">
            Environment variables. Backend values live in{' '}
            <Mono>backend/.env</Mono>; the frontend reads{' '}
            <Mono>frontend/.env.local</Mono>. Changing either needs a restart.
          </p>
          <dl className="mt-3 space-y-3">
            {[
              {
                name: 'MISTRAL_API_KEY',
                detail: 'Required. Without it no document can be generated.',
              },
              {
                name: 'MISTRAL_MODEL',
                detail: 'Optional. Defaults to mistral-large-latest.',
              },
              {
                name: 'LLM_TIMEOUT',
                detail:
                  'Optional, in seconds. Unset, the deadline is derived from the request’s token budget — a full document is allowed about 230s.',
              },
              {
                name: 'VITE_API_URL',
                detail: `Frontend only. Currently ${API_BASE_URL}.`,
              },
              {
                name: 'FORMATLY_DATA_DIR',
                detail: 'Optional. Where generated documents are written.',
              },
            ].map((v) => (
              <div key={v.name}>
                <Mono>{v.name}</Mono>
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted">
                  {v.detail}
                </p>
              </div>
            ))}
          </dl>
        </GlassCard>
      </div>
    </div>
  )
}

/* ── small presentational helpers ─────────────────────────────────────────── */

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-sm font-semibold text-ink">{children}</div>
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="shrink-0 text-[11px] font-medium uppercase tracking-wide text-neutral-500">
        {label}
      </dt>
      <dd className="flex min-w-0 items-center text-right text-xs text-ink">
        {children}
      </dd>
    </div>
  )
}

function Mono({ children }: { children: React.ReactNode }) {
  return <span className="font-mono text-[11px] text-ink">{children}</span>
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      aria-hidden
      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
        ok ? 'bg-emerald-500' : 'bg-amber-500'
      }`}
    />
  )
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-3 rounded-lg border border-line bg-surface-2 px-3 py-2 text-[11px] leading-relaxed text-muted">
      {children}
    </p>
  )
}
