import { motion } from 'framer-motion'

interface ActivityRingProps {
  value: number
  maxValue: number
  size?: number
  strokeWidth?: number
  color?: string
  backgroundColor?: string
  label?: string
  animate?: boolean
}

export function ActivityRing({
  value,
  maxValue,
  size = 120,
  strokeWidth = 12,
  color = '#6D00FF',
  backgroundColor = '#E5E5E5',
  label,
  animate = true,
}: ActivityRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const percentage = Math.min((value / maxValue) * 100, 100)
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={backgroundColor}
          strokeWidth={strokeWidth}
          fill="none"
          className="opacity-20 dark:opacity-10"
        />
        
        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={animate ? { strokeDashoffset: circumference } : { strokeDashoffset }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </svg>
      
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold">{Math.round(percentage)}%</span>
        {label && (
          <span className="text-xs text-muted-foreground">{label}</span>
        )}
      </div>
    </div>
  )
}

interface ActivityRingsProps {
  move: number
  moveGoal: number
  exercise: number
  exerciseGoal: number
  stand: number
  standGoal: number
  size?: number
}

export function ActivityRings({
  move,
  moveGoal,
  exercise,
  exerciseGoal,
  stand,
  standGoal,
  size = 200,
}: ActivityRingsProps) {
  const rings = [
    { value: move, goal: moveGoal, color: '#FF3B30', label: 'Move' },
    { value: exercise, goal: exerciseGoal, color: '#00C851', label: 'Exercise' },
    { value: stand, goal: standGoal, color: '#00D9FF', label: 'Stand' },
  ]

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {rings.map((ring, index) => {
        const ringSize = size - index * 40
        const offset = (size - ringSize) / 2
        
        return (
          <div
            key={ring.label}
            className="absolute"
            style={{
              top: offset,
              left: offset,
            }}
          >
            <ActivityRing
              value={ring.value}
              maxValue={ring.goal}
              size={ringSize}
              strokeWidth={12}
              color={ring.color}
            />
          </div>
        )
      })}
      
      {/* Center labels */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-3xl font-bold">
            {Math.round((move / moveGoal) * 100)}%
          </div>
          <div className="text-sm text-muted-foreground">Daily Goal</div>
        </div>
      </div>
    </div>
  )
}