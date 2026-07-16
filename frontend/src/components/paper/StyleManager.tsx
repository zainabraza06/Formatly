import { useRef, useState } from 'react'
import clsx from 'clsx'
import { paperApi, type StyleSummary } from '../../lib/paperApi'

/** Lists built-in styles and lets the user define their own — either by uploading a
 *  reference DOCX (formatting is learned from it) or by editing a stylesheet JSON. */
export function StyleManager({ styles, onChanged }: {
  styles: StyleSummary[]
  onChanged: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  const [base, setBase] = useState('report')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  const builtins = styles.filter((s) => s.builtin === 'true')
  const custom = styles.filter((s) => s.builtin === 'false')

  const upload = async (file: File | undefined) => {
    if (!file) return
    if (!name.trim()) {
      setError('Give the style a name first')
      return
    }
    setBusy(true); setError(null)
    try {
      await paperApi.styleFromDocx(file, name.trim(), base)
      setName('')
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not learn the style')
    } finally {
      setBusy(false)
    }
  }

  const openEditor = async (id: string) => {
    setError(null)
    try {
      const sheet = await paperApi.getStyle(id)
      sheet.name = `${sheet.name} (copy)`
      sheet.id = ''
      sheet.builtin = false
      setDraft(JSON.stringify(sheet, null, 2))
      setEditing(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load style')
    }
  }

  const saveDraft = async () => {
    setBusy(true); setError(null)
    try {
      await paperApi.createStyle(JSON.parse(draft))
      setEditing(null); setDraft('')
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Invalid stylesheet JSON')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id: string) => {
    setBusy(true)
    try {
      await paperApi.deleteStyle(id)
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Styles</div>

      {error && <div className="rounded-lg bg-red-500/10 px-2 py-1.5 text-[11px] text-red-500">{error}</div>}

      <div>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">Built-in</div>
        <div className="flex flex-wrap gap-1.5">
          {builtins.map((s) => (
            <span key={s.id} className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-neutral-700 dark:text-neutral-200">
              {s.name}
              <button onClick={() => openEditor(s.id)} title="Duplicate & customise"
                      className="text-neutral-400 hover:text-violet-500">✎</button>
            </span>
          ))}
        </div>
      </div>

      {custom.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">My styles</div>
          <div className="space-y-1.5">
            {custom.map((s) => (
              <div key={s.id} className="rounded-lg border border-violet-500/20 bg-violet-500/10 p-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-violet-700 dark:text-violet-300">{s.name}</span>
                  <span className="text-[9px] text-neutral-400">
                    {s.columns} col · {s.heading_scheme} · {s.table_borders} rules
                  </span>
                  <span className="flex-1" />
                  <button onClick={() => openEditor(s.id)} className="text-neutral-400 hover:text-violet-500">✎</button>
                  <button onClick={() => remove(s.id)} disabled={busy}
                          className="text-neutral-400 hover:text-red-500">×</button>
                </div>
                {s.derived_from && (
                  <div className="mt-1 text-[9px] text-neutral-500">
                    Learned from <span className="font-medium">{s.derived_from}</span>
                    {s.detected && (
                      <>
                        {' — read '}
                        {s.detected.split(',').filter(Boolean).map((d) => (
                          <span key={d} className="mr-1 rounded bg-emerald-500/15 px-1 text-emerald-600 dark:text-emerald-300">
                            {d.replace(/_/g, ' ')}
                          </span>
                        ))}
                        <span className="text-neutral-400">· the rest came from the base style</span>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* learn a style from a reference document */}
      <div className="rounded-xl border border-dashed border-white/15 p-3">
        <div className="mb-2 text-[11px] font-semibold text-neutral-700 dark:text-neutral-200">
          Define your own format
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Style name"
                 className="min-w-32 flex-1 rounded-lg border border-white/10 bg-white/10 px-2 py-1.5 text-[11px] text-neutral-900 outline-none dark:bg-white/5 dark:text-neutral-100" />
          <select value={base} onChange={(e) => setBase(e.target.value)}
                  className="rounded-lg border border-white/10 bg-white/10 px-2 py-1.5 text-[11px] text-neutral-900 outline-none dark:bg-white/5 dark:text-neutral-100">
            {builtins.map((s) => <option key={s.id} value={s.id}>base: {s.name}</option>)}
          </select>
          <input ref={fileRef} type="file" accept=".docx" hidden
                 onChange={(e) => upload(e.target.files?.[0])} />
          <button onClick={() => fileRef.current?.click()} disabled={busy}
                  className="rounded-lg bg-neutral-900 px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-50 dark:bg-white dark:text-neutral-950">
            {busy ? 'Reading…' : 'Learn from DOCX'}
          </button>
        </div>
        <div className="mt-1.5 text-[10px] text-neutral-400">
          Upload a document you like — its fonts, sizes, alignment, page setup <em>and conventions</em>{' '}
          (columns, heading numbering, caption placement, table rules) become a reusable style.
          The base style only fills in whatever the sample doesn't reveal.
        </div>
      </div>

      {editing && (
        <div className="space-y-2 rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="text-[11px] font-semibold text-neutral-700 dark:text-neutral-200">
            Edit stylesheet JSON
          </div>
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={12}
                    className={clsx('w-full rounded-lg border border-white/10 bg-neutral-900 p-2',
                                    'font-mono text-[10px] leading-relaxed text-neutral-200 outline-none')} />
          <div className="flex gap-2">
            <button onClick={saveDraft} disabled={busy}
                    className="rounded-lg bg-neutral-900 px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-50 dark:bg-white dark:text-neutral-950">
              Save style
            </button>
            <button onClick={() => { setEditing(null); setDraft('') }}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-neutral-500">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
