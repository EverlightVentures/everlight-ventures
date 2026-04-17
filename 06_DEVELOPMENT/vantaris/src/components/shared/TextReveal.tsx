'use client'

import { motion } from 'framer-motion'

interface TextRevealProps {
  text: string
  className?: string
  style?: React.CSSProperties
  delay?: number
  staggerSpeed?: number
}

export function TextReveal({ text, className = '', style = {}, delay = 0, staggerSpeed = 0.03 }: TextRevealProps) {
  const words = text.split(' ')

  return (
    <motion.span
      className={className}
      style={{ display: 'inline', ...style }}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: staggerSpeed, delayChildren: delay } },
      }}>
      {words.map((word, wi) => (
        <span key={wi} className="inline-block mr-[0.3em]">
          {word.split('').map((char, ci) => (
            <motion.span
              key={ci}
              className="inline-block"
              variants={{
                hidden: { opacity: 0, y: 40, rotateX: -40 },
                visible: {
                  opacity: 1, y: 0, rotateX: 0,
                  transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] },
                },
              }}>
              {char}
            </motion.span>
          ))}
        </span>
      ))}
    </motion.span>
  )
}
