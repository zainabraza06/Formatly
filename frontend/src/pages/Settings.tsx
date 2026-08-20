import { GlassCard } from '../components/GlassCard'

export function Settings() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <GlassCard>
        <div className="text-sm font-semibold text-ink">Settings</div>
        <div className="mt-1 text-xs text-muted">
          Minimal settings panel for this demo build.
        </div>

        <div className="mt-4 space-y-2 text-xs text-muted">
          <div>
            <span className="font-semibold text-ink">Frontend API URL:</span>{' '}
            <span className="font-mono">VITE_API_URL</span> (default: http://127.0.0.1:8000; override via env or `.env.local`)
          </div>
          <div>
            <span className="font-semibold text-ink">Mistral:</span>{' '}
            Set <span className="font-mono">MISTRAL_API_KEY</span> for AI generation (console.mistral.ai).
            Optional: <span className="font-mono">MISTRAL_MODEL</span> (default: <span className="font-mono">mistral-large-latest</span>).
          </div>
          <div>
            <span className="font-semibold text-ink">Request timeout:</span>{' '}
            Derived from the token budget by default — a full document gets ~230s.
            Override with <span className="font-mono">LLM_TIMEOUT</span> (seconds).
          </div>
        </div>
      </GlassCard>

      <GlassCard>
        <div className="text-sm font-semibold text-ink">Notes</div>
        <div className="mt-3 space-y-2 text-xs text-muted">
          <div>• DOCX templates support style extraction + cloning.</div>
          <div>• PDF/image templates are accepted with limited cloning fidelity.</div>
          <div>• Drafts are auto-saved after generation and edits.</div>
        </div>
      </GlassCard>
    </div>
  )
}
