import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

const EASE = [0.16, 1, 0.3, 1] as const

/**
 * Content that arrives as it is scrolled to.
 *
 * Once, not every time it passes: a section that re-animates on the way back up
 * is a page fighting the person reading it. With the system set to less
 * movement it still fades, because appearing from nothing with no transition
 * reads as a glitch, but it does not travel.
 */
export function Reveal({
  children,
  delay = 0,
  y = 16,
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
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-64px' }}
      transition={{ duration: 0.5, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  )
}

/**
 * A group whose children arrive one after another. The delay between them is
 * short on purpose: 60ms reads as a single movement with texture, 200ms reads
 * as waiting for a list to finish loading.
 */
export function RevealGroup({
  children,
  className,
  stagger = 0.06,
  y = 16,
}: {
  children: ReactNode
  className?: string
  stagger?: number
  y?: number
}) {
  const reduced = useReducedMotion()

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, margin: '-64px' }}
      variants={{ shown: { transition: { staggerChildren: stagger } } }}
    >
      {Array.isArray(children)
        ? children.map((child, i) => (
            <motion.div
              key={i}
              variants={{
                hidden: { opacity: 0, y: reduced ? 0 : y },
                shown: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
              }}
            >
              {child}
            </motion.div>
          ))
        : children}
    </motion.div>
  )
}
