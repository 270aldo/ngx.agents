'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Goal } from '@/types'
import { 
  Target, 
  TrendingUp, 
  Calendar, 
  CheckCircle2, 
  XCircle,
  PauseCircle,
  Plus,
  Edit,
  Trash2,
  Flag
} from 'lucide-react'
import { format, differenceInDays, parseISO } from 'date-fns'
import { cn } from '@/utils/cn'
import progressService from '@/services/progress'
import { toast } from 'react-hot-toast'

interface GoalTrackerProps {
  userId: string
  goals: Goal[]
  onGoalUpdate?: (goals: Goal[]) => void
  className?: string
}

const categoryConfig = {
  weight: { label: 'Peso', icon: Target, color: 'purple' },
  body_fat: { label: 'Grasa Corporal', icon: TrendingUp, color: 'red' },
  muscle: { label: 'Masa Muscular', icon: TrendingUp, color: 'blue' },
  performance: { label: 'Rendimiento', icon: Flag, color: 'green' },
  custom: { label: 'Personalizado', icon: Target, color: 'gray' }
}

export function GoalTracker({ userId, goals: initialGoals, onGoalUpdate, className }: GoalTrackerProps) {
  const [goals, setGoals] = useState<Goal[]>(initialGoals)
  const [showNewGoal, setShowNewGoal] = useState(false)
  const [editingGoal, setEditingGoal] = useState<string | null>(null)
  const [newGoal, setNewGoal] = useState<Partial<Goal>>({
    title: '',
    target_value: 0,
    current_value: 0,
    unit: 'kg',
    target_date: format(new Date(Date.now() + 90 * 24 * 60 * 60 * 1000), 'yyyy-MM-dd'),
    category: 'weight',
    status: 'active'
  })

  const handleCreateGoal = async () => {
    try {
      const created = await progressService.createGoal({
        ...newGoal,
        user_id: userId
      })
      const updatedGoals = [...goals, created]
      setGoals(updatedGoals)
      onGoalUpdate?.(updatedGoals)
      setShowNewGoal(false)
      setNewGoal({
        title: '',
        target_value: 0,
        current_value: 0,
        unit: 'kg',
        target_date: format(new Date(Date.now() + 90 * 24 * 60 * 60 * 1000), 'yyyy-MM-dd'),
        category: 'weight',
        status: 'active'
      })
      toast.success('Meta creada exitosamente')
    } catch (error) {
      toast.error('Error al crear la meta')
    }
  }

  const handleUpdateGoal = async (goalId: string, updates: Partial<Goal>) => {
    try {
      const updated = await progressService.updateGoal(goalId, updates)
      const updatedGoals = goals.map(g => g.id === goalId ? updated : g)
      setGoals(updatedGoals)
      onGoalUpdate?.(updatedGoals)
      setEditingGoal(null)
      toast.success('Meta actualizada')
    } catch (error) {
      toast.error('Error al actualizar la meta')
    }
  }

  const handleDeleteGoal = async (goalId: string) => {
    if (!confirm('¿Estás seguro de eliminar esta meta?')) return
    
    try {
      await progressService.deleteGoal(goalId)
      const updatedGoals = goals.filter(g => g.id !== goalId)
      setGoals(updatedGoals)
      onGoalUpdate?.(updatedGoals)
      toast.success('Meta eliminada')
    } catch (error) {
      toast.error('Error al eliminar la meta')
    }
  }

  const calculateProgress = (goal: Goal) => {
    const progress = (goal.current_value / goal.target_value) * 100
    return Math.min(Math.max(progress, 0), 100)
  }

  const getDaysRemaining = (targetDate: string) => {
    return differenceInDays(parseISO(targetDate), new Date())
  }

  const getStatusIcon = (status: Goal['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'paused':
        return <PauseCircle className="w-5 h-5 text-yellow-500" />
      default:
        return null
    }
  }

  const activeGoals = goals.filter(g => g.status === 'active')
  const completedGoals = goals.filter(g => g.status === 'completed')

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="border-b border-gray-100">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold text-navy-700">
            Metas y Objetivos
          </CardTitle>
          <Button
            onClick={() => setShowNewGoal(!showNewGoal)}
            className="bg-purple-500 hover:bg-purple-600"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nueva Meta
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6">
        {/* New Goal Form */}
        {showNewGoal && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h3 className="text-lg font-semibold mb-4">Crear Nueva Meta</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <Label htmlFor="title">Título de la Meta</Label>
                <Input
                  id="title"
                  value={newGoal.title}
                  onChange={(e) => setNewGoal({ ...newGoal, title: e.target.value })}
                  placeholder="Ej: Perder 10kg en 3 meses"
                />
              </div>
              
              <div>
                <Label htmlFor="category">Categoría</Label>
                <select
                  id="category"
                  value={newGoal.category}
                  onChange={(e) => setNewGoal({ ...newGoal, category: e.target.value as Goal['category'] })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  {Object.entries(categoryConfig).map(([key, config]) => (
                    <option key={key} value={key}>{config.label}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <Label htmlFor="target_date">Fecha Objetivo</Label>
                <Input
                  id="target_date"
                  type="date"
                  value={newGoal.target_date}
                  onChange={(e) => setNewGoal({ ...newGoal, target_date: e.target.value })}
                />
              </div>
              
              <div>
                <Label htmlFor="current_value">Valor Actual</Label>
                <div className="flex gap-2">
                  <Input
                    id="current_value"
                    type="number"
                    value={newGoal.current_value}
                    onChange={(e) => setNewGoal({ ...newGoal, current_value: Number(e.target.value) })}
                  />
                  <Input
                    value={newGoal.unit}
                    onChange={(e) => setNewGoal({ ...newGoal, unit: e.target.value })}
                    className="w-20"
                    placeholder="kg"
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="target_value">Valor Objetivo</Label>
                <Input
                  id="target_value"
                  type="number"
                  value={newGoal.target_value}
                  onChange={(e) => setNewGoal({ ...newGoal, target_value: Number(e.target.value) })}
                />
              </div>
            </div>
            
            <div className="flex justify-end gap-2 mt-4">
              <Button
                variant="ghost"
                onClick={() => setShowNewGoal(false)}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleCreateGoal}
                className="bg-purple-500 hover:bg-purple-600"
                disabled={!newGoal.title || !newGoal.target_value}
              >
                Crear Meta
              </Button>
            </div>
          </div>
        )}

        {/* Active Goals */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Metas Activas</h3>
          {activeGoals.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No tienes metas activas. ¡Crea una para comenzar!
            </p>
          ) : (
            activeGoals.map(goal => {
              const progress = calculateProgress(goal)
              const daysRemaining = getDaysRemaining(goal.target_date)
              const config = categoryConfig[goal.category]
              const Icon = config.icon

              return (
                <div
                  key={goal.id}
                  className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                >
                  {editingGoal === goal.id ? (
                    // Edit mode
                    <div className="space-y-3">
                      <Input
                        value={goal.current_value}
                        onChange={(e) => handleUpdateGoal(goal.id, { current_value: Number(e.target.value) })}
                        type="number"
                        placeholder="Valor actual"
                      />
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditingGoal(null)}
                        >
                          Cancelar
                        </Button>
                        <Button
                          size="sm"
                          className="bg-purple-500 hover:bg-purple-600"
                          onClick={() => setEditingGoal(null)}
                        >
                          Guardar
                        </Button>
                      </div>
                    </div>
                  ) : (
                    // View mode
                    <>
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-start gap-3">
                          <div className={cn(
                            "p-2 rounded-lg",
                            `bg-${config.color}-100`
                          )}>
                            <Icon className={cn("w-5 h-5", `text-${config.color}-600`)} />
                          </div>
                          <div>
                            <h4 className="font-semibold text-gray-900">{goal.title}</h4>
                            <p className="text-sm text-gray-500">
                              {goal.current_value} / {goal.target_value} {goal.unit}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditingGoal(goal.id)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteGoal(goal.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div className="mb-3">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Progreso</span>
                          <span className="font-medium">{progress.toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={cn(
                              "h-2 rounded-full transition-all duration-300",
                              progress >= 100 ? "bg-green-500" : "bg-purple-500"
                            )}
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      </div>

                      {/* Footer info */}
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-1 text-gray-500">
                          <Calendar className="w-4 h-4" />
                          {daysRemaining > 0 ? (
                            <span>{daysRemaining} días restantes</span>
                          ) : (
                            <span className="text-red-600">Vencida hace {Math.abs(daysRemaining)} días</span>
                          )}
                        </div>
                        {progress >= 100 && (
                          <span className="text-green-600 font-medium">¡Meta alcanzada! 🎉</span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )
            })
          )}
        </div>

        {/* Completed Goals Summary */}
        {completedGoals.length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Metas Completadas</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {completedGoals.slice(0, 3).map(goal => (
                <div key={goal.id} className="p-3 bg-green-50 rounded-lg border border-green-200">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                    <span className="font-medium text-green-900 text-sm">{goal.title}</span>
                  </div>
                  <p className="text-xs text-green-700">
                    Completada el {format(parseISO(goal.updated_at || goal.created_at), 'dd/MM/yyyy')}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}