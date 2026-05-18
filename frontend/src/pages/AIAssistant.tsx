import { useMemo, useState } from 'react'
import { GlassCard } from '../components/GlassCard'
import { api } from '../lib/api'
import type { ChatMessage } from '../types/api'

export function AIAssistant() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Tell me what you want to change: rewrite sections, adjust tone, add bullets, or tighten structure.',
    },
  ])
  const [busy, setBusy] = useState(false)

  const lastUser = useMemo(() => [...messages].reverse().find((m) => m.role === 'user')?.content, [messages])

  async function send() {
    if (!input.trim()) return
    const next: ChatMessage = { role: 'user', content: input.trim() }
    setMessages((m) => [...m, next])
    setInput('')
    setBusy(true)
    try {
      const res = await api.chat({ messages: [...messages, next] })
      setMessages((m) => [...m, { role: 'assistant', content: res.message }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <GlassCard className="xl:col-span-2">
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">AI Assistant</div>
        <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
          Chat-style helper for document editing guidance.
        </div>

        <div className="mt-4 h-[420px] space-y-2 overflow-auto rounded-2xl border border-white/10 bg-white/5 p-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm ${
                m.role === 'user'
                  ? 'ml-auto bg-neutral-900 text-white dark:bg-white dark:text-neutral-950'
                  : 'bg-white/10 text-neutral-900 dark:bg-white/5 dark:text-neutral-100'
              }`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          ))}
        </div>

        <div className="mt-3 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask DocPilot AI…"
            className="flex-1 rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-sm text-neutral-900 outline-none placeholder:text-neutral-500 focus:ring-2 focus:ring-sky-400/30 dark:bg-white/5 dark:text-neutral-100"
            onKeyDown={(e) => {
              if (e.key === 'Enter') void send()
            }}
          />
          <button
            type="button"
            onClick={() => void send()}
            disabled={busy}
            className="rounded-xl bg-neutral-900 px-4 py-2 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-60 dark:bg-white dark:text-neutral-950"
          >
            {busy ? 'Thinking…' : 'Send'}
          </button>
        </div>
      </GlassCard>

      <GlassCard>
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Tips</div>
        <div className="mt-3 space-y-2 text-xs text-neutral-700 dark:text-neutral-300">
          <div>• “Rewrite Recommendations with 5 bullets”</div>
          <div>• “Make the tone simpler”</div>
          <div>• “Shorten the introduction”</div>
        </div>
        {lastUser ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-[11px] text-neutral-700 dark:text-neutral-300">
            <span className="font-semibold text-neutral-900 dark:text-neutral-100">Last prompt:</span> {lastUser}
          </div>
        ) : null}
      </GlassCard>
    </div>
  )
}
