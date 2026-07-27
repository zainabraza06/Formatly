import { motion } from 'framer-motion'

export function LoadingDots() {
 return (
 <span className="inline-flex items-center gap-1">
 {[0, 1, 2].map((i) => (
 <motion.span
 key={i}
 className="h-1.5 w-1.5 rounded-full bg-ink/50"
 animate={{ opacity: [0.25, 1, 0.25], y: [0, -2, 0] }}
 transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.12 }}
 />
 ))}
 </span>
 )
}
