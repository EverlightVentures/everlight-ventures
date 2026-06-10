import { motion } from 'framer-motion'

export function SkeletonCard() {
  return (
    <div className="card animate-pulse">
      <div className="h-4 bg-dark-700 rounded w-1/3 mb-3"></div>
      <div className="h-8 bg-dark-700 rounded w-2/3 mb-2"></div>
      <div className="h-3 bg-dark-700 rounded w-1/2"></div>
    </div>
  )
}

export function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div className="card animate-pulse">
      <div className="h-6 bg-dark-700 rounded w-1/4 mb-6"></div>
      <div className="space-y-3">
        {[...Array(rows)].map((_, i) => (
          <div key={i} className="flex gap-4">
            {[...Array(columns)].map((_, j) => (
              <div
                key={j}
                className="h-4 bg-dark-700 rounded flex-1"
                style={{ opacity: 1 - (i * 0.1) }}
              ></div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function SkeletonChart() {
  return (
    <div className="card animate-pulse">
      <div className="h-6 bg-dark-700 rounded w-1/3 mb-6"></div>
      <div className="h-64 bg-dark-700 rounded"></div>
    </div>
  )
}

export function PageLoader() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center justify-center h-screen"
    >
      <div className="text-center">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 180, 360],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="w-16 h-16 mx-auto mb-4 rounded-xl bg-gradient-to-br from-neon-blue to-neon-purple"
        />
        <p className="text-gray-400 animate-pulse">Loading...</p>
      </div>
    </motion.div>
  )
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="text-center py-12"
    >
      <motion.div
        animate={{
          y: [0, -10, 0],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="w-20 h-20 mx-auto mb-4 bg-dark-800 rounded-full flex items-center justify-center"
      >
        {Icon && <Icon className="w-10 h-10 text-gray-600" />}
      </motion.div>
      <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
      <p className="text-gray-400 mb-6 max-w-md mx-auto">{description}</p>
      {action}
    </motion.div>
  )
}
