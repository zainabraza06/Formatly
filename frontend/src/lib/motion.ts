import { useEffect, useState } from 'react'

/**
 * The product's motion vocabulary: 150–250ms, ease-out, no bounce and no
 * overshoot. Anything that moves uses one of these, so the whole app
 * decelerates the same way.
 */
export const EASE_OUT = [0.16, 1, 0.3, 1] as const

export const DURATION = {
  fast: 0.15,
  base: 0.2,
  slow: 0.25,
} as const

/** True when the reader has asked their system for less movement. */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true,
  )

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReduced(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return reduced
}

/**
 * Framer Motion props for something arriving on screen. When the reader has
 * asked for less movement it still fades — appearing from nothing with no
 * transition at all reads as a glitch — but it does not travel.
 */
export function enter(reduced: boolean, y = 6) {
  return {
    initial: { opacity: 0, y: reduced ? 0 : y },
    animate: { opacity: 1, y: 0 },
    transition: { duration: DURATION.base, ease: EASE_OUT },
  }
}
