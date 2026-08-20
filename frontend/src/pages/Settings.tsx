import { useEffect, useState, type FormEvent } from 'react'
import { GlassCard } from '../components/GlassCard'
import { useAuth } from '../context/AuthContext'
import { authApi, getToken, type AuthUser } from '../lib/auth'
import { btnPrimary, field as uiField } from '../lib/ui'

/** Account settings: the things that belong to the person using this, not to
 *  the machine it runs on. Email is the account's identity, so it is shown but
 *  not editable. */
export function Settings() {
  const { user, refreshUser, logout } = useAuth()

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Settings</h1>
        <p className="mt-0.5 text-sm text-muted">Manage your account.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ProfileCard user={user} onSaved={refreshUser} />
        <PasswordCard />
        <SessionCard user={user} onSignOut={logout} />
      </div>
    </div>
  )
}

/* ── profile ──────────────────────────────────────────────────────────────── */

function ProfileCard({
  user,
  onSaved,
}: {
  user: AuthUser | null
  onSaved: (u: AuthUser) => void
}) {
  const [name, setName] = useState(user?.name || '')
  const [state, setState] = useState<FormState>({ kind: 'idle' })

  useEffect(() => setName(user?.name || ''), [user?.name])

  const unchanged = name.trim() === (user?.name || '').trim()

  const save = async (e: FormEvent) => {
    e.preventDefault()
    const token = getToken()
    if (!token || !name.trim() || unchanged) return
    setState({ kind: 'busy' })
    try {
      onSaved(await authApi.updateName(token, name.trim()))
      setState({ kind: 'done', message: 'Name updated.' })
    } catch (err) {
      setState({ kind: 'error', message: message(err) })
    }
  }

  return (
    <GlassCard>
      <CardTitle>Profile</CardTitle>
      <form onSubmit={save} className="mt-3 space-y-3">
        <Field label="Display name">
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              setState({ kind: 'idle' })
            }}
            placeholder="Your name"
            className={uiField}
          />
        </Field>

        <Field label="Email" hint="Your email identifies the account and cannot be changed here.">
          <input value={user?.email || ''} readOnly disabled className={`${uiField} opacity-60`} />
        </Field>

        <div className="flex items-center gap-3 pt-1">
          <button
            type="submit"
            disabled={state.kind === 'busy' || !name.trim() || unchanged}
            className={btnPrimary}
          >
            {state.kind === 'busy' ? 'Saving…' : 'Save changes'}
          </button>
          <Feedback state={state} />
        </div>
      </form>
    </GlassCard>
  )
}

/* ── password ─────────────────────────────────────────────────────────────── */

const MIN_PASSWORD = 6

function PasswordCard() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [state, setState] = useState<FormState>({ kind: 'idle' })

  // Checked here as well as on the server so the mistake is caught before a
  // round trip, not because the server's check is optional.
  const mismatch = confirm.length > 0 && next !== confirm
  const tooShort = next.length > 0 && next.length < MIN_PASSWORD
  const ready =
    current.length > 0 && next.length >= MIN_PASSWORD && next === confirm && next !== current

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const token = getToken()
    if (!token || !ready) return
    setState({ kind: 'busy' })
    try {
      await authApi.changePassword(token, current, next)
      setCurrent('')
      setNext('')
      setConfirm('')
      setState({ kind: 'done', message: 'Password changed.' })
    } catch (err) {
      setState({ kind: 'error', message: message(err) })
    }
  }

  return (
    <GlassCard>
      <CardTitle>Password</CardTitle>
      <form onSubmit={submit} className="mt-3 space-y-3">
        <Field label="Current password">
          <input
            type="password"
            value={current}
            onChange={(e) => {
              setCurrent(e.target.value)
              setState({ kind: 'idle' })
            }}
            autoComplete="current-password"
            className={uiField}
          />
        </Field>

        <Field label="New password" hint={`At least ${MIN_PASSWORD} characters.`}>
          <input
            type="password"
            value={next}
            onChange={(e) => {
              setNext(e.target.value)
              setState({ kind: 'idle' })
            }}
            autoComplete="new-password"
            className={uiField}
          />
        </Field>

        <Field label="Confirm new password">
          <input
            type="password"
            value={confirm}
            onChange={(e) => {
              setConfirm(e.target.value)
              setState({ kind: 'idle' })
            }}
            autoComplete="new-password"
            className={uiField}
          />
        </Field>

        {tooShort && <Hint tone="warn">Use at least {MIN_PASSWORD} characters.</Hint>}
        {mismatch && <Hint tone="warn">The two new passwords do not match.</Hint>}
        {next.length > 0 && next === current && (
          <Hint tone="warn">The new password must differ from the current one.</Hint>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button type="submit" disabled={state.kind === 'busy' || !ready} className={btnPrimary}>
            {state.kind === 'busy' ? 'Updating…' : 'Change password'}
          </button>
          <Feedback state={state} />
        </div>
      </form>
    </GlassCard>
  )
}

/* ── session ──────────────────────────────────────────────────────────────── */

function SessionCard({
  user,
  onSignOut,
}: {
  user: AuthUser | null
  onSignOut: () => void
}) {
  return (
    <GlassCard>
      <CardTitle>Session</CardTitle>
      <dl className="mt-3 space-y-2.5">
        {user?.created_at && (
          <div className="flex items-baseline justify-between gap-4">
            <dt className="text-[11px] font-medium uppercase tracking-wide text-neutral-500">
              Member since
            </dt>
            <dd className="text-xs text-ink">
              {new Date(user.created_at).toLocaleDateString()}
            </dd>
          </div>
        )}
      </dl>
      <button
        onClick={onSignOut}
        className="mt-4 rounded-lg border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-surface-2"
      >
        Sign out
      </button>
    </GlassCard>
  )
}

/* ── shared bits ──────────────────────────────────────────────────────────── */

type FormState =
  | { kind: 'idle' }
  | { kind: 'busy' }
  | { kind: 'done'; message: string }
  | { kind: 'error'; message: string }

function message(err: unknown): string {
  return err instanceof Error ? err.message : 'Something went wrong.'
}

function CardTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-sm font-semibold text-ink">{children}</div>
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
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

function Hint({ tone, children }: { tone: 'warn'; children: React.ReactNode }) {
  return (
    <p className={`text-[11px] ${tone === 'warn' ? 'text-amber-600' : 'text-muted'}`}>
      {children}
    </p>
  )
}

function Feedback({ state }: { state: FormState }) {
  if (state.kind === 'done') {
    return <span className="text-[11px] text-emerald-600">{state.message}</span>
  }
  if (state.kind === 'error') {
    return <span className="text-[11px] text-danger">{state.message}</span>
  }
  return null
}
