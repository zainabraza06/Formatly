import { useState, type FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import { authApi, getToken, type AuthUser } from '../lib/auth'
import { Button, Card, CardHeader, Field, Input, useToast } from '../components/ui'
import { SignOutIcon } from '../components/icons'

const MIN_PASSWORD = 6

/**
 * Account settings: the things that belong to the person using this, not to
 * the machine it runs on. Email is the account's identity, so it is shown but
 * not editable.
 */
export function Settings() {
  const { user, refreshUser, logout } = useAuth()

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Settings</h1>
        <p className="mt-1 text-sm text-muted">Manage your account.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Keyed on the stored name: when the account changes underneath it,
            the card remounts with the new value instead of syncing in an
            effect. */}
        <ProfileCard key={user?.name ?? ''} user={user} onSaved={refreshUser} />
        <PasswordCard />
        <SessionCard user={user} onSignOut={logout} />
      </div>
    </div>
  )
}

/* ── profile ──────────────────────────────────────────────────────────────── */

function ProfileCard({ user, onSaved }: { user: AuthUser | null; onSaved: (u: AuthUser) => void }) {
  const toast = useToast()
  const [name, setName] = useState(user?.name || '')
  const [busy, setBusy] = useState(false)

  const unchanged = name.trim() === (user?.name || '').trim()

  const save = async (e: FormEvent) => {
    e.preventDefault()
    const token = getToken()
    if (!token || !name.trim() || unchanged) return
    setBusy(true)
    try {
      onSaved(await authApi.updateName(token, name.trim()))
      toast.success('Name updated')
    } catch (err) {
      toast.error('Could not update your name', message(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Profile" description="How you are named in the app." />
      <form onSubmit={save} className="mt-4 space-y-4">
        <Field label="Display name">
          {(props) => (
            <Input
              {...props}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              autoComplete="name"
            />
          )}
        </Field>

        <Field label="Email" hint="Your email identifies the account and cannot be changed here.">
          {(props) => <Input {...props} value={user?.email || ''} readOnly disabled />}
        </Field>

        <Button type="submit" variant="primary" loading={busy} disabled={!name.trim() || unchanged}>
          Save changes
        </Button>
      </form>
    </Card>
  )
}

/* ── password ─────────────────────────────────────────────────────────────── */

function PasswordCard() {
  const toast = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)

  // Checked here as well as on the server so the mistake is caught before a
  // round trip, not because the server's check is optional.
  const mismatch = confirm.length > 0 && next !== confirm
  const tooShort = next.length > 0 && next.length < MIN_PASSWORD
  const sameAsCurrent = next.length > 0 && next === current
  const ready =
    current.length > 0 && next.length >= MIN_PASSWORD && next === confirm && !sameAsCurrent

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const token = getToken()
    if (!token || !ready) return
    setBusy(true)
    try {
      await authApi.changePassword(token, current, next)
      setCurrent('')
      setNext('')
      setConfirm('')
      toast.success('Password changed', 'Use the new one next time you sign in.')
    } catch (err) {
      toast.error('Could not change your password', message(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Password" description="Change the password you sign in with." />
      <form onSubmit={submit} className="mt-4 space-y-4">
        <Field label="Current password">
          {(props) => (
            <Input {...props} type="password" value={current}
                   onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
          )}
        </Field>

        <Field
          label="New password"
          hint={`At least ${MIN_PASSWORD} characters.`}
          error={
            tooShort ? `Use at least ${MIN_PASSWORD} characters.`
            : sameAsCurrent ? 'The new password must be different from the current one.'
            : null
          }
        >
          {(props) => (
            <Input {...props} type="password" value={next}
                   onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
          )}
        </Field>

        <Field
          label="Confirm new password"
          error={mismatch ? 'The two new passwords do not match.' : null}
        >
          {(props) => (
            <Input {...props} type="password" value={confirm}
                   onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          )}
        </Field>

        <Button type="submit" variant="primary" loading={busy} disabled={!ready}>
          Change password
        </Button>
      </form>
    </Card>
  )
}

/* ── session ──────────────────────────────────────────────────────────────── */

function SessionCard({ user, onSignOut }: { user: AuthUser | null; onSignOut: () => void }) {
  return (
    <Card>
      <CardHeader title="Session" description="This browser, signed in as you." />
      <dl className="mt-4 space-y-2">
        <Row label="Signed in as" value={user?.email || '—'} />
        {user?.created_at && (
          <Row label="Member since" value={new Date(user.created_at).toLocaleDateString()} />
        )}
      </dl>
      <Button variant="secondary" className="mt-4" onClick={onSignOut} leadingIcon={<SignOutIcon />}>
        Sign out
      </Button>
    </Card>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="truncate text-sm text-ink">{value}</dd>
    </div>
  )
}

function message(err: unknown): string {
  return err instanceof Error ? err.message : 'Something went wrong. Please try again.'
}
