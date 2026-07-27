import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { btnPrimary, field } from '../lib/ui'

export function Login() {
  const { login, signup } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const from = location.state?.from || '/app/compose'

  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await signup(email, password, name)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-4 text-ink">
      <motion.form
        onSubmit={submit}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-sm rounded-2xl border border-line bg-surface p-7"
      >
        <div className="mb-1 flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-[13px] font-semibold text-accent-fg">
            F
          </div>
          <span className="text-base font-semibold tracking-tight">Formatly</span>
        </div>
        <p className="mb-6 text-sm text-muted">
          {mode === 'login'
            ? 'Sign in to your documents and versions.'
            : 'Create an account to save your work.'}
        </p>

        {mode === 'signup' && (
          <Field label="Name">
            <input value={name} onChange={(e) => setName(e.target.value)} className={field} placeholder="Your name" />
          </Field>
        )}
        <Field label="Email">
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={field} placeholder="you@example.com" />
        </Field>
        <Field label="Password">
          <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className={field} placeholder="••••••••" />
        </Field>

        {error && (
          <div className="mb-3 rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
            {error}
          </div>
        )}

        <button type="submit" disabled={busy} className={`${btnPrimary} w-full py-2.5`}>
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>

        <button
          type="button"
          onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(null) }}
          className="mt-4 w-full text-center text-xs text-muted transition-colors hover:text-ink"
        >
          {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
        </button>
      </motion.form>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="mb-3 block">
      <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  )
}
