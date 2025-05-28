'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  ReferenceLine
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, Calendar, Filter } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/types'
import { format, parseISO } from 'date-fns'
import { cn } from '@/utils/cn'

interface ProgressChartProps {
  data: Progress[]
  metric?: 'weight' | 'body_fat' | 'muscle_mass' | 'measurements'
  height?: number
  showTrend?: boolean
  goal?: number
  className?: string
}

type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y' | 'ALL'

const metricConfig = {
  weight: {
    label: 'Peso',
    unit: 'kg',
    color: '#6D00FF',
    gradientId: 'weightGradient'
  },
  body_fat: {
    label: 'Grasa Corporal',
    unit: '%',
    color: '#FF6B6B',
    gradientId: 'bodyFatGradient'
  },
  muscle_mass: {
    label: 'Masa Muscular',
    unit: 'kg',
    color: '#4ECDC4',
    gradientId: 'muscleGradient'
  }
}

export function ProgressChart({
  data,
  metric = 'weight',
  height = 300,
  showTrend = true,
  goal,
  className
}: ProgressChartProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('3M')
  const [chartType, setChartType] = useState<'line' | 'area'>('area')

  const config = metricConfig[metric as keyof typeof metricConfig]
  if (!config) return null

  // Transform data for chart
  const chartData = data.map(entry => ({
    date: format(parseISO(entry.date), 'MMM dd'),
    value: metric === 'weight' ? entry.weight : 
           metric === 'body_fat' ? entry.body_fat_percentage :
           metric === 'muscle_mass' ? entry.weight && entry.body_fat_percentage ? 
             entry.weight * (1 - entry.body_fat_percentage / 100) : null : null,
    fullDate: entry.date
  })).filter(item => item.value !== null)

  // Calculate trend
  const calculateTrend = () => {
    if (chartData.length < 2) return { value: 0, percentage: 0, direction: 'neutral' as const }
    
    const first = chartData[0].value!
    const last = chartData[chartData.length - 1].value!
    const change = last - first
    const percentage = (change / first) * 100

    return {
      value: Math.abs(change),
      percentage: Math.abs(percentage),
      direction: change > 0 ? 'up' : change < 0 ? 'down' : 'neutral'
    } as const
  }

  const trend = calculateTrend()

  // Calculate statistics
  const stats = {
    current: chartData[chartData.length - 1]?.value || 0,
    best: Math.min(...chartData.map(d => d.value!)),
    average: chartData.reduce((sum, d) => sum + d.value!, 0) / chartData.length
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="text-sm font-medium text-gray-900">{label}</p>
          <p className="text-lg font-bold" style={{ color: config.color }}>
            {payload[0].value.toFixed(1)} {config.unit}
          </p>
        </div>
      )
    }
    return null
  }

  const TrendIndicator = () => (
    <div className="flex items-center gap-2">
      {trend.direction === 'up' ? (
        <TrendingUp className="w-4 h-4 text-green-500" />
      ) : trend.direction === 'down' ? (
        <TrendingDown className="w-4 h-4 text-red-500" />
      ) : (
        <Minus className="w-4 h-4 text-gray-500" />
      )}
      <span className={cn(
        "text-sm font-medium",
        trend.direction === 'up' && metric === 'muscle_mass' ? 'text-green-600' :
        trend.direction === 'down' && metric !== 'muscle_mass' ? 'text-green-600' :
        'text-red-600'
      )}>
        {trend.value.toFixed(1)} {config.unit} ({trend.percentage.toFixed(1)}%)
      </span>
    </div>
  )

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold text-navy-700">
              {config.label}
            </CardTitle>
            {showTrend && <TrendIndicator />}
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex bg-gray-100 rounded-lg p-1">
              {(['1W', '1M', '3M', '6M', '1Y', 'ALL'] as TimeRange[]).map(range => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={cn(
                    "px-3 py-1 text-xs font-medium rounded transition-all",
                    timeRange === range
                      ? "bg-white text-purple-600 shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  )}
                >
                  {range}
                </button>
              ))}
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setChartType(chartType === 'line' ? 'area' : 'line')}
            >
              <Filter className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6">
        <ResponsiveContainer width="100%" height={height}>
          {chartType === 'area' ? (
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={config.gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={config.color} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={config.color} stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis 
                dataKey="date" 
                stroke="#6B7280"
                fontSize={12}
              />
              <YAxis 
                stroke="#6B7280"
                fontSize={12}
                domain={['dataMin - 1', 'dataMax + 1']}
              />
              <Tooltip content={<CustomTooltip />} />
              {goal && (
                <ReferenceLine 
                  y={goal} 
                  stroke="#10B981" 
                  strokeDasharray="5 5"
                  label={{ value: "Meta", position: "right" }}
                />
              )}
              <Area
                type="monotone"
                dataKey="value"
                stroke={config.color}
                strokeWidth={3}
                fill={`url(#${config.gradientId})`}
                dot={{ fill: config.color, r: 4, strokeWidth: 2, stroke: '#FFFFFF' }}
                activeDot={{ r: 6, stroke: config.color, strokeWidth: 2, fill: '#FFFFFF' }}
              />
            </AreaChart>
          ) : (
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis 
                dataKey="date" 
                stroke="#6B7280"
                fontSize={12}
              />
              <YAxis 
                stroke="#6B7280"
                fontSize={12}
                domain={['dataMin - 1', 'dataMax + 1']}
              />
              <Tooltip content={<CustomTooltip />} />
              {goal && (
                <ReferenceLine 
                  y={goal} 
                  stroke="#10B981" 
                  strokeDasharray="5 5"
                  label={{ value: "Meta", position: "right" }}
                />
              )}
              <Line
                type="monotone"
                dataKey="value"
                stroke={config.color}
                strokeWidth={3}
                dot={{ fill: config.color, r: 4, strokeWidth: 2, stroke: '#FFFFFF' }}
                activeDot={{ r: 6, stroke: config.color, strokeWidth: 2, fill: '#FFFFFF' }}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
        
        {/* Statistics */}
        <div className="mt-6 grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
          <div className="text-center">
            <p className="text-sm text-gray-600">Actual</p>
            <p className="text-lg font-semibold" style={{ color: config.color }}>
              {stats.current.toFixed(1)} {config.unit}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600">Mejor</p>
            <p className="text-lg font-semibold text-navy-600">
              {stats.best.toFixed(1)} {config.unit}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600">Promedio</p>
            <p className="text-lg font-semibold text-gray-600">
              {stats.average.toFixed(1)} {config.unit}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}