import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Button, Field, Input } from '../components/ui'
import { Logo } from '../components/Logo'
import { WarningIcon } from '../components/icons'

const MIN_PASSWORD = 6

/**
 * Sign in, or sign up — the same form either way, because at this size the
 * difference is one field.
 *
 * Validation happens where the mistake is, before the round trip: an empty
 * email and a five-character password are answered by the field itself rather
 * than by the server a second later.
 */
export function Login() {
  const { login, signup } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const from = location.state?.from || '/app'

  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [touched, setTouched] = useState(false)
  const [busy, setBusy] = useState(false)

  const emailError = touched && !email.trim()
    ? 'Enter the email address you signed up with.'
    : touched && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
      ? 'That does not look like an email address.'
      : null

  const passwordError = touched && password.length < MIN_PASSWORD
    ? `Passwords are at least ${MIN_PASSWORD} characters.`
    : null

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    setError(null)
    if (!email.trim() || password.length < MIN_PASSWORD) return

    setBusy(true)
    try {
      if (mode === 'login') await login(email.trim(), password)
      else await signup(email.trim(), password, name.trim())
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas px-4 py-10">
      <div className="mx-auto w-full max-w-sm">
        <Link to="/" className="inline-flex rounded-md">
          <Logo to={null} />
        </Link>

        <form
          onSubmit={submit}
          noValidate
          className="mt-6 animate-fade-up rounded-xl border border-line bg-surface p-6 shadow-sm"
        >
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            {mode === 'login' ? 'Sign in' : 'Create your account'}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {mode === 'login'
              ? 'Your documents and their version history are waiting.'
              : 'Free while Formatly is in beta — no card needed.'}
          </p>

          <div className="mt-5 space-y-4">
            {mode === 'signup' && (
              <Field label="Name" optional>
                {(props) => (
                  <Input
                    {...props}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    placeholder="Your name"
                  />
                )}
              </Field>
            )}

            <Field label="Email" required error={emailError}>
              {(props) => (
                <Input
                  {...props}
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onBlur={() => setTouched(true)}
                  autoComplete="email"
                  placeholder="you@example.com"
                />
              )}
            </Field>

            <Field
              label="Password"
              required
              error={passwordError}
              hint={mode === 'signup' ? `At least ${MIN_PASSWORD} characters.` : undefined}
            >
              {(props) => (
                <Input
                  {...props}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setTouched(true)}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  placeholder="••••••••"
                />
              )}
            </Field>
          </div>

          {error && (
            <p role="alert" className="mt-4 flex items-start gap-2 rounded-md border border-danger/25 bg-danger-soft px-3 py-2 text-xs text-danger">
              <WarningIcon className="mt-px h-4 w-4 shrink-0" />
              {error}
            </p>
          )}

          <Button type="submit" variant="primary" size="lg" fullWidth loading={busy} className="mt-5">
            {mode === 'login' ? 'Sign in' : 'Create account'}
          </Button>

          <p className="mt-4 text-center text-sm text-muted">
            {mode === 'login' ? 'No account yet?' : 'Already have an account?'}{' '}
            <button
              type="button"
              onClick={() => {
                setMode(mode === 'login' ? 'signup' : 'login')
                setError(null)
                setTouched(false)
              }}
              className="rounded-sm font-medium text-brand-ink hover:underline"
            >
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </button>
          </p>
        </form>

        <p className="mt-4 text-center text-xs text-faint">
          <Link to="/" className="rounded-sm hover:text-muted">← Back to the home page</Link>
        </p>
      </div>
    </div>
  )
}
