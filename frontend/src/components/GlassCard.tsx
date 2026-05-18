import type { PropsWithChildren } from 'react'
import clsx from 'clsx'
import { motion } from 'framer-motion'

export function GlassCard({
  children,
  className,
}: PropsWithChildren<{ className?: string }>) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={clsx(
        'rounded-2xl border border-white/10 bg-white/10 p-5 shadow-sm backdrop-blur-md',
        'dark:border-white/10 dark:bg-white/5',
        className,
      )}
    >
      {children}
    </motion.div>
  )
}
