import { GlassCard } from '../components/GlassCard'

export function Settings() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <GlassCard>
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Settings</div>
        <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
          Minimal settings panel for this demo build.
        </div>

        <div className="mt-4 space-y-2 text-xs text-neutral-700 dark:text-neutral-300">
          <div>
            <span className="font-semibold text-neutral-900 dark:text-neutral-100">Frontend API URL:</span>{' '}
            <span className="font-mono">VITE_API_URL</span> (default: http://127.0.0.1:8000; override via env or `.env.local`)
          </div>
          <div>
            <span className="font-semibold text-neutral-900 dark:text-neutral-100">OpenAI:</span>{' '}
            Set <span className="font-mono">OPENAI_API_KEY</span> for higher quality generation.
          </div>
        </div>
      </GlassCard>

      <GlassCard>
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Notes</div>
        <div className="mt-3 space-y-2 text-xs text-neutral-700 dark:text-neutral-300">
          <div>• DOCX templates support style extraction + cloning.</div>
          <div>• PDF/image templates are accepted with limited cloning fidelity.</div>
          <div>• Drafts are auto-saved after generation and edits.</div>
        </div>
      </GlassCard>
    </div>
  )
}
