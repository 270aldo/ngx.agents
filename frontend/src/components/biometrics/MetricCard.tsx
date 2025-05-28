import { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { cn } from '@/utils/cn'

interface MetricCardProps {
  title: string
  value: string | number
  unit?: string
  change?: number
  changeType?: 'positive' | 'negative' | 'neutral'
  icon?: ReactNode
  color?: string
  loading?: boolean
}

export function MetricCard({
  title,
  value,
  unit,
  change,
  changeType = 'neutral',
  icon,
  color = 'primary',
  loading,
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (!change) return null
    
    if (change > 0) {
      return <TrendingUp className="h-4 w-4" />
    } else if (change < 0) {
      return <TrendingDown className="h-4 w-4" />
    }
    return <Minus className="h-4 w-4" />
  }

  const getTrendColor = () => {
    if (changeType === 'positive') {
      return change && change > 0 ? 'text-green-500' : 'text-red-500'
    } else if (changeType === 'negative') {
      return change && change > 0 ? 'text-red-500' : 'text-green-500'
    }
    return 'text-gray-500'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="relative overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {icon && (
            <div className={cn(
              'rounded-full p-2',
              color === 'primary' && 'bg-primary/20 text-primary',
              color === 'green' && 'bg-green-500/20 text-green-500',
              color === 'blue' && 'bg-blue-500/20 text-blue-500',
              color === 'red' && 'bg-red-500/20 text-red-500',
              color === 'purple' && 'bg-purple-500/20 text-purple-500',
              color === 'yellow' && 'bg-yellow-500/20 text-yellow-500'
            )}>
              {icon}
            </div>
          )}
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              <div className="h-8 w-24 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
              <div className="h-4 w-16 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
            </div>
          ) : (
            <>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold">{value}</span>
                {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
              </div>
              {change !== undefined && (
                <div className={cn('flex items-center gap-1 text-sm mt-1', getTrendColor())}>
                  {getTrendIcon()}
                  <span>{Math.abs(change)}%</span>
                  <span className="text-muted-foreground">from last week</span>
                </div>
              )}
            </>
          )}
        </CardContent>
        
        {/* Decorative gradient */}
        <div className={cn(
          'absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r',
          color === 'primary' && 'from-primary/20 to-primary',
          color === 'green' && 'from-green-500/20 to-green-500',
          color === 'blue' && 'from-blue-500/20 to-blue-500',
          color === 'red' && 'from-red-500/20 to-red-500',
          color === 'purple' && 'from-purple-500/20 to-purple-500',
          color === 'yellow' && 'from-yellow-500/20 to-yellow-500'
        )} />
      </Card>
    </motion.div>
  )
}