import { useState, type FormEvent, type ReactNode } from 'react'
import { useAuth } from '../context/AuthContext'
import { authApi, getToken, type AuthUser } from '../lib/auth'
import { Button, Card, Field, Input, useToast } from '../components/ui'
import { AppearGroup } from '../components/motion/Appear'
import { Page, PageHeader } from '../components/layout/Page'
import { useReportError } from '../hooks/useReportError'
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
    // One column, with a measure. Settings in a two-column grid leaves the
    // third card sitting alone beside a hole, and puts a form field 1200px
    // from the label that names it.
    <Page width="narrow">
      <PageHeader title="Settings" description="Manage your account." />

      <AppearGroup className="space-y-8" stagger={0.06}>
        {/* Keyed on the stored name: when the account changes underneath it,
            the card remounts with the new value instead of syncing in an
            effect. */}
        <ProfileCard key={user?.name ?? ''} user={user} onSaved={refreshUser} />
        <PasswordCard />
        <SessionCard user={user} onSignOut={logout} />
      </AppearGroup>
    </Page>
  )
}

/* ── profile ──────────────────────────────────────────────────────────────── */

function ProfileCard({ user, onSaved }: { user: AuthUser | null; onSaved: (u: AuthUser) => void }) {
  const toast = useToast()
  const report = useReportError()
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
      report(err, 'update your name')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section title="Profile" description="How you are named in the app.">
      <form onSubmit={save} className="space-y-4">
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

        <div className="flex justify-end border-t border-line pt-4">
          <Button type="submit" variant="primary" loading={busy} disabled={!name.trim() || unchanged}>
            Save changes
          </Button>
        </div>
      </form>
    </Section>
  )
}

/* ── password ─────────────────────────────────────────────────────────────── */

function PasswordCard() {
  const toast = useToast()
  const report = useReportError()
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
      report(err, 'change your password')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section title="Password" description="Change the password you sign in with.">
      <form onSubmit={submit} className="space-y-4">
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

        <div className="flex justify-end border-t border-line pt-4">
          <Button type="submit" variant="primary" loading={busy} disabled={!ready}>
            Change password
          </Button>
        </div>
      </form>
    </Section>
  )
}

/* ── session ──────────────────────────────────────────────────────────────── */

function SessionCard({ user, onSignOut }: { user: AuthUser | null; onSignOut: () => void }) {
  return (
    <Section title="Session" description="This browser, signed in as you.">
      <dl className="divide-y divide-line">
        <Row label="Signed in as" value={user?.email || '—'} />
        {user?.created_at && (
          <Row label="Member since" value={new Date(user.created_at).toLocaleDateString()} />
        )}
      </dl>
      <div className="flex justify-end border-t border-line pt-4">
        <Button variant="secondary" onClick={onSignOut} leadingIcon={<SignOutIcon />}>
          Sign out
        </Button>
      </div>
    </Section>
  )
}

/**
 * A settings section: its name and purpose above the panel it belongs to,
 * rather than inside it. The heading then sits on the page's own left edge,
 * which is what makes three sections read as one column.
 */
function Section({
  title, description, children,
}: { title: string; description: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="text-base font-medium text-ink">{title}</h2>
      <p className="mt-1 text-sm text-muted">{description}</p>
      <Card className="mt-4">{children}</Card>
    </section>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2 first:pt-0">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="truncate text-sm text-ink">{value}</dd>
    </div>
  )
}
