import { useState } from 'react'
import { GlassCard } from '../components/GlassCard'
import { UploadDropzone } from '../components/UploadDropzone'
import { api } from '../lib/api'
import type { TemplateAnalyzeResponse } from '../types/api'

export function Templates() {
  const [tpl, setTpl] = useState<TemplateAnalyzeResponse | null>(null)

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <GlassCard>
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Upload template</div>
        <div className="mt-1 text-xs text-neutral-700 dark:text-neutral-300">
          Templates are used for cloning structure and style. DOCX provides best results.
        </div>
        <div className="mt-3">
          <UploadDropzone
            uploaded={tpl}
            onUpload={async (file) => {
              const r = await api.uploadTemplate(file)
              setTpl(r)
              return r
            }}
          />
        </div>
      </GlassCard>

      <GlassCard>
        <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">How cloning works</div>
        <div className="mt-3 space-y-2 text-xs text-neutral-700 dark:text-neutral-300">
          <div>1) Upload template → analyze style/layout.</div>
          <div>2) Generate a new document using the template id.</div>
          <div>3) Export to DOCX/PDF with matching formatting.</div>
        </div>

        {tpl ? (
          <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs font-semibold text-neutral-900 dark:text-neutral-100">Extracted style</div>
            <pre className="mt-2 max-h-60 overflow-auto rounded-xl bg-black/10 p-3 text-[11px] text-neutral-800 dark:bg-white/5 dark:text-neutral-100">
              {JSON.stringify(tpl.extracted_style, null, 2)}
            </pre>
          </div>
        ) : null}
      </GlassCard>
    </div>
  )
}
