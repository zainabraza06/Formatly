import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

const EASE = [0.16, 1, 0.3, 1] as const

/**
 * Content that arrives when it mounts, rather than when it is scrolled to.
 *
 * Inside the app almost nothing is below the fold, so a scroll reveal would
 * never fire; what matters here is that a screen assembles in the order the
 * eye reads it instead of appearing whole.
 */
export function Appear({
  children,
  delay = 0,
  y = 8,
  className,
}: {
  children: ReactNode
  delay?: number
  y?: number
  className?: string
}) {
  const reduced = useReducedMotion()

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: reduced ? 0 : y }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  )
}

/**
 * Several things arriving one after another. The stagger is short — this is a
 * screen being drawn, not a story being told.
 */
export function AppearGroup({
  children,
  className,
  stagger = 0.05,
  delay = 0,
  y = 8,
}: {
  children: ReactNode
  className?: string
  stagger?: number
  delay?: number
  y?: number
}) {
  const reduced = useReducedMotion()
  const items = Array.isArray(children) ? children : [children]

  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="shown"
      variants={{ shown: { transition: { staggerChildren: stagger, delayChildren: delay } } }}
    >
      {items.map((child, i) => (
        <motion.div
          key={i}
          variants={{
            hidden: { opacity: 0, y: reduced ? 0 : y },
            shown: { opacity: 1, y: 0, transition: { duration: 0.3, ease: EASE } },
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  )
}
