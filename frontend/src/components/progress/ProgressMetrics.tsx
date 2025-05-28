'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress, ProgressStats, Measurements } from '@/types'
import { 
  TrendingUp, 
  TrendingDown, 
  Activity,
  Ruler,
  Calendar,
  Award,
  Zap,
  Target,
  BarChart3,
  ArrowUp,
  ArrowDown,
  Minus
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { format, parseISO, differenceInDays } from 'date-fns'
import { 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from 'recharts'

interface ProgressMetricsProps {
  currentProgress: Progress
  progressHistory: Progress[]
  stats: ProgressStats
  className?: string
}

export function ProgressMetrics({
  currentProgress,
  progressHistory,
  stats,
  className
}: ProgressMetricsProps) {
  // Calculate changes and trends
  const previousProgress = progressHistory[progressHistory.length - 2]
  
  const calculateChange = (current?: number, previous?: number) => {
    if (!current || !previous) return null
    return current - previous
  }

  const calculatePercentageChange = (current?: number, previous?: number) => {
    if (!current || !previous) return null
    return ((current - previous) / previous) * 100
  }

  const weightChange = calculateChange(currentProgress.weight, previousProgress?.weight)
  const bodyFatChange = calculateChange(
    currentProgress.body_fat_percentage, 
    previousProgress?.body_fat_percentage
  )

  // Prepare measurement data for radar chart
  const getMeasurementData = () => {
    const current = currentProgress.measurements || {}
    const previous = previousProgress?.measurements || {}
    
    return [
      {
        metric: 'Pecho',
        current: current.chest || 0,
        previous: previous.chest || 0,
        ideal: 100 // Example ideal values
      },
      {
        metric: 'Cintura',
        current: current.waist || 0,
        previous: previous.waist || 0,
        ideal: 80
      },
      {
        metric: 'Caderas',
        current: current.hips || 0,
        previous: previous.hips || 0,
        ideal: 95
      },
      {
        metric: 'Bíceps',
        current: current.biceps || 0,
        previous: previous.biceps || 0,
        ideal: 40
      },
      {
        metric: 'Muslos',
        current: current.thighs || 0,
        previous: previous.thighs || 0,
        ideal: 60
      }
    ]
  }

  // Prepare weekly progress data
  const getWeeklyProgress = () => {
    const last7Weeks = []
    const now = new Date()
    
    for (let i = 6; i >= 0; i--) {
      const weekStart = new Date(now)
      weekStart.setDate(weekStart.getDate() - (i * 7))
      
      const weekData = progressHistory.filter(p => {
        const date = parseISO(p.date)
        const diff = differenceInDays(date, weekStart)
        return diff >= 0 && diff < 7
      })
      
      const avgWeight = weekData.length > 0
        ? weekData.reduce((sum, p) => sum + (p.weight || 0), 0) / weekData.length
        : null
      
      last7Weeks.push({
        week: `S${7 - i}`,
        weight: avgWeight,
        entries: weekData.length
      })
    }
    
    return last7Weeks
  }

  const MetricCard = ({ 
    title, 
    value, 
    unit, 
    change, 
    icon: Icon,
    color = 'purple',
    reverseColors = false
  }: {
    title: string
    value: number | string
    unit: string
    change?: number | null
    icon: React.FC<{ className?: string }>
    color?: string
    reverseColors?: boolean
  }) => {
    const isPositive = change && change > 0
    const isNegative = change && change < 0
    const changeColor = reverseColors 
      ? (isPositive ? 'text-red-600' : isNegative ? 'text-green-600' : 'text-gray-600')
      : (isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-600')

    return (
      <div className="bg-white p-4 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between mb-2">
          <div className={cn(
            "p-2 rounded-lg",
            `bg-${color}-100`
          )}>
            <Icon className={cn("w-5 h-5", `text-${color}-600`)} />
          </div>
          {change !== null && change !== undefined && (
            <div className={cn("flex items-center gap-1 text-sm", changeColor)}>
              {isPositive ? <ArrowUp className="w-4 h-4" /> : 
               isNegative ? <ArrowDown className="w-4 h-4" /> : 
               <Minus className="w-4 h-4" />}
              <span className="font-medium">
                {Math.abs(change).toFixed(1)}{unit}
              </span>
            </div>
          )}
        </div>
        <p className="text-sm text-gray-600 mb-1">{title}</p>
        <p className="text-2xl font-bold text-gray-900">
          {typeof value === 'number' ? value.toFixed(1) : value}{unit}
        </p>
      </div>
    )
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="text-sm font-medium text-gray-900">{label}</p>
          <p className="text-sm text-gray-600">
            Peso: {payload[0].value?.toFixed(1) || '-'} kg
          </p>
          <p className="text-xs text-gray-500">
            {payload[0].payload.entries} registros
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Peso Actual"
          value={currentProgress.weight || 0}
          unit="kg"
          change={weightChange}
          icon={TrendingUp}
          color="purple"
          reverseColors={true}
        />
        
        <MetricCard
          title="Grasa Corporal"
          value={currentProgress.body_fat_percentage || 0}
          unit="%"
          change={bodyFatChange}
          icon={Activity}
          color="red"
          reverseColors={true}
        />
        
        <MetricCard
          title="Racha Actual"
          value={stats.streak_days}
          unit=" días"
          change={null}
          icon={Zap}
          color="yellow"
        />
        
        <MetricCard
          title="Total Perdido"
          value={Math.abs(stats.total_weight_lost || 0)}
          unit="kg"
          change={null}
          icon={Award}
          color="green"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weekly Progress Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-navy-700 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Progreso Semanal
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={getWeeklyProgress()}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis 
                  dataKey="week" 
                  stroke="#6B7280"
                  fontSize={12}
                />
                <YAxis 
                  stroke="#6B7280"
                  fontSize={12}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar 
                  dataKey="weight" 
                  fill="#6D00FF"
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Measurements Radar Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-navy-700 flex items-center gap-2">
              <Ruler className="w-5 h-5" />
              Medidas Corporales
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={getMeasurementData()}>
                <PolarGrid stroke="#E5E7EB" />
                <PolarAngleAxis 
                  dataKey="metric" 
                  fontSize={12}
                  stroke="#6B7280"
                />
                <PolarRadiusAxis 
                  angle={90} 
                  domain={[0, 'auto']}
                  fontSize={10}
                  stroke="#6B7280"
                />
                <Radar 
                  name="Actual" 
                  dataKey="current" 
                  stroke="#6D00FF" 
                  fill="#6D00FF" 
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
                <Radar 
                  name="Anterior" 
                  dataKey="previous" 
                  stroke="#0A0628" 
                  fill="#0A0628" 
                  fillOpacity={0.1}
                  strokeWidth={2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-navy-700">
            Estadísticas Detalladas
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-gray-600 mb-1">Días Activo</p>
              <p className="text-xl font-bold text-gray-900">
                {differenceInDays(new Date(), parseISO(stats.start_date))}
              </p>
            </div>
            
            <div>
              <p className="text-sm text-gray-600 mb-1">Entrenamientos</p>
              <p className="text-xl font-bold text-gray-900">
                {stats.total_workouts}
              </p>
            </div>
            
            <div>
              <p className="text-sm text-gray-600 mb-1">Mejor Racha</p>
              <p className="text-xl font-bold text-gray-900">
                {stats.best_streak} días
              </p>
            </div>
            
            <div>
              <p className="text-sm text-gray-600 mb-1">Logros</p>
              <p className="text-xl font-bold text-gray-900">
                {stats.total_achievements}
              </p>
            </div>
          </div>

          {/* Body Composition Changes */}
          {currentProgress.measurements && (
            <div className="mt-6 pt-6 border-t border-gray-100">
              <h4 className="text-sm font-semibold text-gray-900 mb-4">
                Cambios en Medidas (cm)
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {Object.entries(currentProgress.measurements).map(([key, value]) => {
                  const previousValue = previousProgress?.measurements?.[key as keyof Measurements]
                  const change = calculateChange(value, previousValue)
                  
                  return (
                    <div key={key} className="text-center">
                      <p className="text-xs text-gray-600 capitalize mb-1">
                        {key.replace('_', ' ')}
                      </p>
                      <p className="text-lg font-semibold text-gray-900">
                        {value}
                      </p>
                      {change !== null && (
                        <p className={cn(
                          "text-xs font-medium mt-1",
                          change > 0 ? "text-green-600" : change < 0 ? "text-red-600" : "text-gray-500"
                        )}>
                          {change > 0 ? '+' : ''}{change.toFixed(1)}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}