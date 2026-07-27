import clsx from 'clsx'
import { motion } from 'framer-motion'
import type { PipelineStep } from '../types/api'

function statusClasses(status: PipelineStep['status']) {
  if (status === 'done') return 'bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-500/30'
  if (status === 'running') return 'bg-sky-500/20 text-sky-200 ring-1 ring-sky-500/30'
  if (status === 'error') return 'bg-rose-500/20 text-rose-200 ring-1 ring-rose-500/30'
  return 'bg-surface-20/10 text-neutral-200 ring-1 ring-white/10'
}

export function PipelineSteps({ steps }: { steps: PipelineStep[] }) {
  return (
    <div className="flex flex-col gap-2">
      {steps.map((s) => (
        <motion.div
          key={s.name}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2 }}
          className={clsx(
            'flex items-center justify-between rounded-xl px-3 py-2 text-sm',
            'bg-surface-2 ',
            statusClasses(s.status),
          )}
        >
          <div className="font-medium">{s.name}</div>
          <div className="truncate pl-3 text-xs opacity-90">{s.detail || s.status}</div>
        </motion.div>
      ))}
    </div>
  )
}
