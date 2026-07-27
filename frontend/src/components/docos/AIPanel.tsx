import { useState } from 'react'
import { motion } from 'framer-motion'
import type { PanelState } from '../../hooks/useDocOS'

const SUGGESTIONS = [
 'Select all headings',
 'Highlight all figures',
 'Remove every horizontal line',
 'Justify every body paragraph',
 'Center every image',
 'Change all references to font size 10',
]

interface Props {
 panel: PanelState
 running: boolean
 disabled: boolean
 onRun: (command: string) => void
}

export function AIPanel({ panel, running, disabled, onRun }: Props) {
 const [input, setInput] = useState('')

 const submit = () => {
 const cmd = input.trim()
 if (!cmd || disabled) return
 onRun(cmd)
 setInput('')
 }

 const pct = panel.progress && panel.progress.total
 ? Math.round((panel.progress.done / panel.progress.total) * 100)
 : running ? 15 : 0

 return (
 <div className="flex h-full flex-col gap-3">
 <div>
 <div className="text-sm font-semibold text-ink">AI Assistant</div>
 <div className="text-xs text-muted">
 {disabled
 ? 'Import a document, then tell the assistant how to format it.'
 : 'Describe a change — every action is shown live in the document.'}
 </div>
 </div>

 <div className="flex gap-2">
 <input
 value={input}
 onChange={(e) => setInput(e.target.value)}
 onKeyDown={(e) => e.key === 'Enter' && submit()}
 disabled={disabled}
 placeholder={disabled ? 'Import a document first…' : 'e.g. Highlight all figures'}
 className="flex-1 rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink outline-none placeholder:text-muted focus:ring-2 focus:ring-focus/40 disabled:opacity-50 "
 />
 <button
 onClick={submit}
 disabled={disabled || !input.trim()}
 className="rounded-xl bg-accent px-4 py-2 text-xs font-medium text-accent-fg hover:opacity-90 disabled:opacity-50 "
 >
 {running ? 'Working…' : 'Run'}
 </button>
 </div>

 <div className="flex flex-wrap gap-1.5">
 {SUGGESTIONS.map((s) => (
 <button
 key={s}
 onClick={() => !disabled && onRun(s)}
 disabled={disabled}
 className="rounded-full border border-line bg-surface-2 px-2.5 py-1 text-[11px] text-muted hover:bg-surface-2 disabled:opacity-50 "
 >
 {s}
 </button>
 ))}
 </div>

 {/* live status */}
 <div className="rounded-2xl border border-line bg-surface-2 p-3">
 {panel.task ? (
 <div className="mb-2 text-xs text-muted">
 Task: <span className="text-ink">{panel.task}</span>
 </div>
 ) : null}

 <div className="flex items-center gap-2 text-sm font-medium text-ink">
 {running && <span className="h-2 w-2 animate-pulse rounded-full bg-ink" />}
 {panel.currentAction}
 </div>

 {panel.reasoning ? (
 <div className="mt-1 text-xs italic text-muted">{panel.reasoning}</div>
 ) : null}

 {(pct > 0 || running) && (
 <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-line">
 <motion.div className="h-full bg-ink" animate={{ width: `${pct}%` }} transition={{ duration: 0.2 }} />
 </div>
 )}

 {panel.provider ? (
 <div className="mt-2 text-[10px] uppercase tracking-wide text-faint">
 via {panel.provider}{panel.source ? ` · ${panel.source}` : ''}
 </div>
 ) : null}

 {panel.error ? (
 <div className="mt-2 rounded-lg border border-danger/30 bg-danger/5 px-2 py-1 text-xs text-danger">{panel.error}</div>
 ) : null}
 </div>

 {panel.upcoming.length > 0 && (
 <Section title="Upcoming actions">
 {panel.upcoming.map((u, i) => (
 <li key={i} className="text-muted">• {u}</li>
 ))}
 </Section>
 )}

 {panel.history.length > 0 && (
 <Section title="Earlier prompts">
 {panel.history.map((h, i) => (
 <li key={i} className="border-l border-line pl-2">
 <div className="text-ink">{h.prompt}</div>
 <div className="text-[10px] text-muted">↳ {h.outcome}</div>
 </li>
 ))}
 </Section>
 )}
 </div>
 )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
 return (
 <div className="rounded-2xl border border-line bg-surface-2 p-3">
 <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-faint">{title}</div>
 <ul className="space-y-0.5 text-xs">{children}</ul>
 </div>
 )
}
