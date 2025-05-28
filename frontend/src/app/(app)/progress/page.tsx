'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { ProgressChart } from '@/components/progress/ProgressChart'
import { GoalTracker } from '@/components/progress/GoalTracker'
import { MilestoneCard } from '@/components/progress/MilestoneCard'
import { ComparisonView } from '@/components/progress/ComparisonView'
import { ProgressMetrics } from '@/components/progress/ProgressMetrics'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import progressService from '@/services/progress'
import { Progress, Goal, Achievement, ProgressStats, Milestone } from '@/types'
import { 
  Plus, 
  TrendingUp, 
  Camera, 
  Target,
  Award,
  BarChart3,
  Download,
  RefreshCw
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import { cn } from '@/utils/cn'

type TabType = 'overview' | 'charts' | 'goals' | 'photos' | 'achievements'

export default function ProgressPage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  
  // Data states
  const [progressHistory, setProgressHistory] = useState<Progress[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [achievements, setAchievements] = useState<Achievement[]>([])
  const [milestones, setMilestones] = useState<Milestone[]>([])
  const [stats, setStats] = useState<ProgressStats | null>(null)

  useEffect(() => {
    if (user) {
      loadAllData()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  const loadAllData = async () => {
    if (!user) return
    
    setLoading(true)
    try {
      const [
        progressData,
        goalsData,
        achievementsData,
        milestonesData,
        statsData
      ] = await Promise.all([
        progressService.getProgress(user.id),
        progressService.getGoals(user.id),
        progressService.getAchievements(user.id),
        progressService.getMilestones(user.id),
        progressService.getProgressStats(user.id)
      ])

      setProgressHistory(progressData)
      setGoals(goalsData)
      setAchievements(achievementsData)
      setMilestones(milestonesData)
      setStats(statsData)
    } catch (_error) {
      toast.error('Error al cargar los datos de progreso')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadAllData()
    setRefreshing(false)
    toast.success('Datos actualizados')
  }

  const handleExportReport = async () => {
    if (!user) return
    
    try {
      const blob = await progressService.exportProgressReport(user.id, 'pdf')
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `progreso-${new Date().toISOString().split('T')[0]}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
      toast.success('Reporte descargado exitosamente')
    } catch (_error) {
      toast.error('Error al exportar el reporte')
    }
  }

  const tabs = [
    { id: 'overview' as TabType, label: 'Resumen', icon: BarChart3 },
    { id: 'charts' as TabType, label: 'Gráficos', icon: TrendingUp },
    { id: 'goals' as TabType, label: 'Metas', icon: Target },
    { id: 'photos' as TabType, label: 'Fotos', icon: Camera },
    { id: 'achievements' as TabType, label: 'Logros', icon: Award }
  ]

  const currentProgress = progressHistory[progressHistory.length - 1]

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          <Skeleton className="h-12 w-64" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Skeleton className="h-64" />
            <Skeleton className="h-64" />
            <Skeleton className="h-64" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-navy-700 mb-2">
            Tu Progreso
          </h1>
          <p className="text-gray-600">
            Monitorea tu evolución y celebra cada logro
          </p>
        </div>
        
        <div className="flex gap-2 mt-4 md:mt-0">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={cn("w-4 h-4 mr-2", refreshing && "animate-spin")} />
            Actualizar
          </Button>
          
          <Button
            variant="outline"
            onClick={handleExportReport}
          >
            <Download className="w-4 h-4 mr-2" />
            Exportar PDF
          </Button>
          
          <Button
            className="bg-purple-500 hover:bg-purple-600"
            onClick={() => {
              // Open modal to add new progress entry
              toast.success('Función próximamente')
            }}
          >
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Registro
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-2 border-b border-gray-200">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-all whitespace-nowrap",
                activeTab === tab.id
                  ? "bg-white text-purple-600 border-b-2 border-purple-600"
                  : "text-gray-600 hover:text-gray-900"
              )}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <>
            {/* Quick Stats */}
            {stats && currentProgress && (
              <ProgressMetrics
                currentProgress={currentProgress}
                progressHistory={progressHistory}
                stats={stats}
              />
            )}
            
            {/* Recent Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ProgressChart
                data={progressHistory}
                metric="weight"
                goal={goals.find(g => g.category === 'weight' && g.status === 'active')?.target_value}
              />
              
              <ProgressChart
                data={progressHistory}
                metric="body_fat"
                goal={goals.find(g => g.category === 'body_fat' && g.status === 'active')?.target_value}
              />
            </div>
          </>
        )}

        {activeTab === 'charts' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ProgressChart
              data={progressHistory}
              metric="weight"
              height={400}
              showTrend
              goal={goals.find(g => g.category === 'weight' && g.status === 'active')?.target_value}
            />
            
            <ProgressChart
              data={progressHistory}
              metric="body_fat"
              height={400}
              showTrend
              goal={goals.find(g => g.category === 'body_fat' && g.status === 'active')?.target_value}
            />
            
            <ProgressChart
              data={progressHistory}
              metric="muscle_mass"
              height={400}
              showTrend
              className="lg:col-span-2"
            />
          </div>
        )}

        {activeTab === 'goals' && (
          <GoalTracker
            userId={user?.id || ''}
            goals={goals}
            onGoalUpdate={setGoals}
          />
        )}

        {activeTab === 'photos' && (
          <ComparisonView
            progressData={progressHistory}
            onPhotoUpload={() => {
              // Refresh data after photo upload
              loadAllData()
            }}
          />
        )}

        {activeTab === 'achievements' && (
          <MilestoneCard
            achievements={achievements}
            milestones={milestones}
            userId={user?.id || ''}
            onUpdate={loadAllData}
          />
        )}
      </div>
    </div>
  )
}