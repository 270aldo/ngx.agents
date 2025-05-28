import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Heart } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/utils/cn'

interface HeartRateMonitorProps {
  currentRate: number
  restingRate?: number
  maxRate?: number
  zone?: 'rest' | 'fat-burn' | 'cardio' | 'peak'
  isLive?: boolean
  history?: { timestamp: string; value: number }[]
}

export function HeartRateMonitor({
  currentRate,
  restingRate = 60,
  maxRate = 180,
  zone = 'rest',
  isLive = false,
  history: _history = [],
}: HeartRateMonitorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()
  const historyRef = useRef<number[]>([])

  useEffect(() => {
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    canvas.width = canvas.offsetWidth * window.devicePixelRatio
    canvas.height = canvas.offsetHeight * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

    let offset = 0

    const draw = () => {
      ctx.clearRect(0, 0, canvas.offsetWidth, canvas.offsetHeight)
      
      // Draw grid
      ctx.strokeStyle = 'rgba(100, 100, 100, 0.2)'
      ctx.lineWidth = 0.5
      for (let i = 0; i < canvas.offsetHeight; i += 20) {
        ctx.beginPath()
        ctx.moveTo(0, i)
        ctx.lineTo(canvas.offsetWidth, i)
        ctx.stroke()
      }

      // Draw heart rate line
      ctx.strokeStyle = getZoneColor(zone)
      ctx.lineWidth = 2
      ctx.beginPath()

      const points = historyRef.current.slice(-100)
      points.forEach((rate, index) => {
        const x = (index / 100) * canvas.offsetWidth - offset
        const y = canvas.offsetHeight - ((rate - 40) / 140) * canvas.offsetHeight
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      
      ctx.stroke()

      offset += 1
      if (offset > canvas.offsetWidth / 100) {
        offset = 0
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [zone])

  useEffect(() => {
    historyRef.current = [...historyRef.current, currentRate].slice(-100)
  }, [currentRate])

  const getZoneColor = (zone: string) => {
    switch (zone) {
      case 'rest': return '#6B7280'
      case 'fat-burn': return '#10B981'
      case 'cardio': return '#F59E0B'
      case 'peak': return '#EF4444'
      default: return '#6B7280'
    }
  }

  const getZoneName = (zone: string) => {
    switch (zone) {
      case 'rest': return 'Resting'
      case 'fat-burn': return 'Fat Burn'
      case 'cardio': return 'Cardio'
      case 'peak': return 'Peak'
      default: return 'Unknown'
    }
  }

  return (
    <Card className="relative overflow-hidden">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Heart className={cn('h-5 w-5', isLive && 'animate-pulse')} />
            Heart Rate
          </CardTitle>
          {isLive && (
            <Badge variant="destructive" className="animate-pulse">
              LIVE
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Current heart rate */}
          <div className="flex items-baseline gap-2">
            <AnimatePresence mode="wait">
              <motion.span
                key={currentRate}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 1.2, opacity: 0 }}
                className="text-4xl font-bold"
                style={{ color: getZoneColor(zone) }}
              >
                {currentRate}
              </motion.span>
            </AnimatePresence>
            <span className="text-sm text-muted-foreground">bpm</span>
          </div>

          {/* Zone indicator */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: getZoneColor(zone) }}
              />
              <span className="font-medium">{getZoneName(zone)}</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <span>Resting: {restingRate}</span>
              <span>•</span>
              <span>Max: {maxRate}</span>
            </div>
          </div>

          {/* Heart rate chart */}
          <div className="relative h-32 bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden">
            <canvas
              ref={canvasRef}
              className="absolute inset-0 w-full h-full"
            />
          </div>

          {/* Zone bars */}
          <div className="space-y-2">
            <div className="text-xs text-muted-foreground mb-1">Heart Rate Zones</div>
            <div className="flex gap-1">
              <div className="flex-1 h-2 bg-gray-400 rounded-sm" title="Rest (50-60%)" />
              <div className="flex-1 h-2 bg-green-500 rounded-sm" title="Fat Burn (60-70%)" />
              <div className="flex-1 h-2 bg-yellow-500 rounded-sm" title="Cardio (70-85%)" />
              <div className="flex-1 h-2 bg-red-500 rounded-sm" title="Peak (85-100%)" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}