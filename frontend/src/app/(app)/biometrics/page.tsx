'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Heart, 
  Footprints, 
  Flame, 
  Moon, 
  Download,
  RefreshCw
} from 'lucide-react'
import { subDays } from 'date-fns'
import { useBiometrics } from '@/services/biometrics'
import { MetricCard } from '@/components/biometrics/MetricCard'
import { TrendChart } from '@/components/biometrics/TrendChart'
import { HeartRateMonitor } from '@/components/biometrics/HeartRateMonitor'
import { ActivityRings } from '@/components/biometrics/ActivityRing'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { biometricsService } from '@/services/biometrics'
import { cn } from '@/utils/cn'

// Mock data for demonstration
const generateMockData = (days: number, baseValue: number, variance: number) => {
  const data = []
  for (let i = days - 1; i >= 0; i--) {
    const date = subDays(new Date(), i)
    data.push({
      timestamp: date.toISOString(),
      value: baseValue + Math.random() * variance - variance / 2,
    })
  }
  return data
}

export default function BiometricsPage() {
  const { metrics, loading, _error } = useBiometrics()
  const [selectedPeriod, setSelectedPeriod] = useState<'day' | 'week' | 'month'>('week')
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  // Mock data for charts
  const [heartRateData] = useState(generateMockData(7, 70, 20))
  const [stepsData] = useState(generateMockData(7, 8000, 3000))
  const [caloriesData] = useState(generateMockData(7, 2200, 500))
  const [sleepData] = useState(generateMockData(7, 7.5, 2))
  const [weightData] = useState(generateMockData(30, 75, 2))

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      const _latest = await biometricsService.fetchLatestMetrics()
      // Handle the refreshed data
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleExport = () => {
    // TODO: Implement data export
    console.log('Exporting biometric data...')
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[...Array(2)].map((_, i) => (
              <Skeleton key={i} className="h-96" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Biometric Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Real-time health metrics and insights
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <Button
              variant={selectedPeriod === 'day' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setSelectedPeriod('day')}
            >
              Day
            </Button>
            <Button
              variant={selectedPeriod === 'week' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setSelectedPeriod('week')}
            >
              Week
            </Button>
            <Button
              variant={selectedPeriod === 'month' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setSelectedPeriod('month')}
            >
              Month
            </Button>
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Heart Rate"
          value={metrics.heart_rate?.value || 72}
          unit="bpm"
          change={-3}
          changeType="positive"
          icon={<Heart className="h-5 w-5" />}
          color="red"
          loading={loading}
        />
        <MetricCard
          title="Steps Today"
          value={metrics.steps?.value || 6784}
          unit="steps"
          change={12}
          changeType="positive"
          icon={<Footprints className="h-5 w-5" />}
          color="blue"
          loading={loading}
        />
        <MetricCard
          title="Calories Burned"
          value={metrics.calories?.value || 1856}
          unit="kcal"
          change={5}
          changeType="positive"
          icon={<Flame className="h-5 w-5" />}
          color="yellow"
          loading={loading}
        />
        <MetricCard
          title="Sleep Quality"
          value={metrics.sleep?.value || 85}
          unit="%"
          change={8}
          changeType="positive"
          icon={<Moon className="h-5 w-5" />}
          color="purple"
          loading={loading}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Activity Rings and Heart Rate */}
        <div className="space-y-6">
          {/* Activity Rings */}
          <Card>
            <CardHeader>
              <CardTitle>Daily Activity</CardTitle>
              <CardDescription>Progress toward your goals</CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center">
              <ActivityRings
                move={450}
                moveGoal={500}
                exercise={25}
                exerciseGoal={30}
                stand={10}
                standGoal={12}
                size={200}
              />
            </CardContent>
          </Card>

          {/* Heart Rate Monitor */}
          <HeartRateMonitor
            currentRate={72}
            restingRate={60}
            maxRate={180}
            zone="rest"
            isLive={true}
            history={heartRateData}
          />
        </div>

        {/* Middle Column - Charts */}
        <div className="lg:col-span-2 space-y-6">
          {/* Steps Chart */}
          <TrendChart
            title="Steps"
            description="Daily step count over time"
            data={stepsData}
            type="bar"
            color="#3B82F6"
            formatValue={(value) => `${Math.round(value).toLocaleString()}`}
          />

          {/* Calories Chart */}
          <TrendChart
            title="Calories Burned"
            description="Daily calorie expenditure"
            data={caloriesData}
            type="area"
            color="#F59E0B"
            formatValue={(value) => `${Math.round(value)} kcal`}
          />

          {/* Sleep Chart */}
          <TrendChart
            title="Sleep Duration"
            description="Hours of sleep per night"
            data={sleepData}
            type="line"
            color="#8B5CF6"
            formatValue={(value) => `${value.toFixed(1)}h`}
          />
        </div>
      </div>

      {/* Bottom Section - Weight Tracking */}
      <div className="mt-8">
        <TrendChart
          title="Weight Trend"
          description="Body weight over the last 30 days"
          data={weightData}
          type="area"
          color="#10B981"
          height={200}
          formatValue={(value) => `${value.toFixed(1)} kg`}
        />
      </div>

      {/* Connected Devices */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Connected Devices</CardTitle>
          <CardDescription>Manage your health tracking devices</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { name: 'Apple Watch', status: 'connected', lastSync: '2 min ago' },
              { name: 'WHOOP 4.0', status: 'connected', lastSync: 'Just now' },
              { name: 'Oura Ring', status: 'connected', lastSync: '15 min ago' },
              { name: 'Garmin Venu', status: 'disconnected', lastSync: '2 days ago' },
            ].map((device) => (
              <motion.div
                key={device.name}
                whileHover={{ scale: 1.02 }}
                className="p-4 border rounded-lg"
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{device.name}</h4>
                  <Badge variant={device.status === 'connected' ? 'success' : 'secondary'}>
                    {device.status}
                  </Badge>
                </div>
                <p className="text-sm text-gray-500">Last sync: {device.lastSync}</p>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}