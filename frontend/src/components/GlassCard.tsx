import type { PropsWithChildren } from 'react'
import clsx from 'clsx'
import { motion } from 'framer-motion'

/**
 * Modern flat card with subtle hover transitions and slight shadow.
 */
export function GlassCard({
  children,
  className,
}: PropsWithChildren<{ className?: string }>) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      whileHover={{ y: -2, boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01)' }}
      className={clsx(
        'rounded-2xl border border-line bg-surface p-6 transition-all duration-200',
        className
      )}
    >
      {children}
    </motion.div>
  )
}
