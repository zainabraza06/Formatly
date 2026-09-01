import { motion } from 'framer-motion'

export function LoadingDots() {
 return (
 <span className="inline-flex items-center gap-1.5 px-1">
 {[0, 1, 2].map((i) => (
 <motion.span
 key={i}
 className="h-2 w-2 rounded-full bg-focus"
 animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
 transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15, ease: 'easeInOut' }}
 />
 ))}
 </span>
 )
}
