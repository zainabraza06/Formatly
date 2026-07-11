import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'

export function Login() {
  const { login, signup } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: string } }
  const from = location.state?.from || '/app/editor'

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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-neutral-100 p-4 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950">
      <motion.form
        onSubmit={submit}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm rounded-2xl border border-black/5 bg-white/80 p-6 shadow-xl backdrop-blur-md dark:border-white/10 dark:bg-neutral-900/70"
      >
        <div className="mb-1 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-purple-600 text-sm font-bold text-white">F</div>
          <span className="text-lg font-bold text-neutral-900 dark:text-neutral-100">Document OS</span>
        </div>
        <p className="mb-5 text-xs text-neutral-500">
          {mode === 'login' ? 'Sign in to your uploads and versions.' : 'Create an account to save your documents.'}
        </p>

        {mode === 'signup' && (
          <Field label="Name">
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="Your name" />
          </Field>
        )}
        <Field label="Email">
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} placeholder="you@example.com" />
        </Field>
        <Field label="Password">
          <input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} placeholder="••••••••" />
        </Field>

        {error && <div className="mb-3 rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</div>}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-white dark:text-neutral-950"
        >
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>

        <button
          type="button"
          onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(null) }}
          className="mt-3 w-full text-center text-xs text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
        >
          {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
        </button>
      </motion.form>
    </div>
  )
}

const inputCls =
  'w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm text-neutral-900 outline-none focus:ring-2 focus:ring-violet-400/40 dark:border-white/10 dark:bg-neutral-950 dark:text-neutral-100'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="mb-3 block">
      <span className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-neutral-500">{label}</span>
      {children}
    </label>
  )
}
