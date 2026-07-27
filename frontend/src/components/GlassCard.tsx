import type { PropsWithChildren } from 'react'
import clsx from 'clsx'
import { motion } from 'framer-motion'

/**
 * Kept the name for compatibility, but this is no longer "glass": a flat
 * editorial card — hairline border, solid surface, no blur or gradient.
 */
export function GlassCard({
  children,
  className,
}: PropsWithChildren<{ className?: string }>) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={clsx('rounded-xl border border-line bg-surface p-5', className)}
    >
      {children}
    </motion.div>
  )
}
