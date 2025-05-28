'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Achievement, Milestone } from '@/types'
import { 
  Trophy, 
  Star, 
  Award, 
  Medal,
  Target,
  Zap,
  Flame,
  TrendingUp,
  Calendar,
  Lock,
  CheckCircle
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { format, parseISO } from 'date-fns'
import { motion, AnimatePresence } from 'framer-motion'
import confetti from 'canvas-confetti'
import progressService from '@/services/progress'
import { toast } from 'react-hot-toast'

interface MilestoneCardProps {
  achievements: Achievement[]
  milestones: Milestone[]
  userId: string
  onUpdate?: () => void
  className?: string
}

const rarityConfig = {
  common: { 
    color: 'gray', 
    bgGradient: 'from-gray-100 to-gray-200',
    borderColor: 'border-gray-300',
    stars: 1 
  },
  rare: { 
    color: 'blue', 
    bgGradient: 'from-blue-100 to-blue-200',
    borderColor: 'border-blue-400',
    stars: 2 
  },
  epic: { 
    color: 'purple', 
    bgGradient: 'from-purple-100 to-purple-200',
    borderColor: 'border-purple-400',
    stars: 3 
  },
  legendary: { 
    color: 'yellow', 
    bgGradient: 'from-yellow-100 to-yellow-200',
    borderColor: 'border-yellow-400',
    stars: 4 
  }
}

const iconMap: Record<string, React.FC<{ className?: string }>> = {
  trophy: Trophy,
  star: Star,
  award: Award,
  medal: Medal,
  target: Target,
  zap: Zap,
  flame: Flame,
  trending: TrendingUp
}

export function MilestoneCard({ 
  achievements, 
  milestones, 
  userId,
  onUpdate,
  className 
}: MilestoneCardProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [showCelebration, setShowCelebration] = useState<string | null>(null)

  const unlockedAchievements = achievements.filter(a => a.unlocked_at)
  const lockedAchievements = achievements.filter(a => !a.unlocked_at)
  
  const categories = ['all', ...new Set(achievements.map(a => a.category))]

  const filteredAchievements = selectedCategory === 'all' 
    ? achievements 
    : achievements.filter(a => a.category === selectedCategory)

  const handleCelebrateMilestone = async (milestoneId: string) => {
    try {
      await progressService.celebrateMilestone(milestoneId)
      
      // Trigger celebration animation
      setShowCelebration(milestoneId)
      
      // Confetti effect
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 }
      })
      
      setTimeout(() => setShowCelebration(null), 3000)
      
      onUpdate?.()
      toast.success('¡Felicitaciones por tu logro!')
    } catch (error) {
      toast.error('Error al celebrar el hito')
    }
  }

  const AchievementItem = ({ achievement }: { achievement: Achievement }) => {
    const isUnlocked = !!achievement.unlocked_at
    const config = rarityConfig[achievement.rarity]
    const Icon = iconMap[achievement.icon] || Trophy

    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className={cn(
          "relative p-4 rounded-lg border-2 transition-all",
          isUnlocked ? config.borderColor : "border-gray-200",
          isUnlocked ? `bg-gradient-to-br ${config.bgGradient}` : "bg-gray-50",
          "hover:shadow-lg cursor-pointer"
        )}
      >
        {!isUnlocked && (
          <div className="absolute inset-0 bg-gray-900 bg-opacity-60 rounded-lg flex items-center justify-center">
            <Lock className="w-8 h-8 text-gray-300" />
          </div>
        )}
        
        <div className="flex items-start gap-3">
          <div className={cn(
            "p-3 rounded-full",
            isUnlocked ? `bg-${config.color}-500` : "bg-gray-300"
          )}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className={cn(
                "font-semibold",
                isUnlocked ? "text-gray-900" : "text-gray-500"
              )}>
                {achievement.title}
              </h4>
              <div className="flex gap-0.5">
                {Array.from({ length: config.stars }).map((_, i) => (
                  <Star 
                    key={i} 
                    className={cn(
                      "w-3 h-3",
                      isUnlocked ? "text-yellow-500 fill-current" : "text-gray-300"
                    )} 
                  />
                ))}
              </div>
            </div>
            
            <p className={cn(
              "text-sm",
              isUnlocked ? "text-gray-600" : "text-gray-400"
            )}>
              {achievement.description}
            </p>
            
            {achievement.progress !== undefined && !isUnlocked && (
              <div className="mt-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">Progreso</span>
                  <span className="font-medium">{achievement.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="h-1.5 bg-purple-500 rounded-full transition-all duration-300"
                    style={{ width: `${achievement.progress}%` }}
                  />
                </div>
              </div>
            )}
            
            {isUnlocked && achievement.unlocked_at && (
              <p className="text-xs text-gray-500 mt-2">
                Desbloqueado el {format(parseISO(achievement.unlocked_at), 'dd/MM/yyyy')}
              </p>
            )}
          </div>
        </div>
      </motion.div>
    )
  }

  const MilestoneItem = ({ milestone }: { milestone: Milestone }) => {
    const isRecent = new Date(milestone.date).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          "p-4 rounded-lg border-2",
          milestone.celebrated ? "border-green-300 bg-green-50" : "border-purple-300 bg-purple-50",
          "relative overflow-hidden"
        )}
      >
        <AnimatePresence>
          {showCelebration === milestone.id && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              className="absolute inset-0 bg-gradient-to-br from-yellow-200 to-purple-200 opacity-30"
            />
          )}
        </AnimatePresence>

        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              {milestone.celebrated ? (
                <CheckCircle className="w-5 h-5 text-green-600" />
              ) : (
                <Star className="w-5 h-5 text-purple-600" />
              )}
              <h4 className="font-semibold text-gray-900">{milestone.title}</h4>
              {isRecent && !milestone.celebrated && (
                <span className="px-2 py-0.5 bg-purple-500 text-white text-xs rounded-full">
                  Nuevo
                </span>
              )}
            </div>
            
            <p className="text-sm text-gray-600 mb-2">{milestone.description}</p>
            
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {format(parseISO(milestone.date), 'dd/MM/yyyy')}
              </div>
              {milestone.value && milestone.unit && (
                <span className="font-medium text-purple-600">
                  {milestone.value} {milestone.unit}
                </span>
              )}
            </div>
          </div>

          {!milestone.celebrated && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleCelebrateMilestone(milestone.id)}
              className="px-3 py-1.5 bg-purple-500 text-white text-sm rounded-lg hover:bg-purple-600 transition-colors"
            >
              Celebrar 🎉
            </motion.button>
          )}
        </div>
      </motion.div>
    )
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Achievements Section */}
      <Card>
        <CardHeader className="border-b border-gray-100">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl font-bold text-navy-700">
              Logros y Medallas
            </CardTitle>
            <div className="flex items-center gap-2 text-sm">
              <Trophy className="w-4 h-4 text-purple-600" />
              <span className="font-medium">
                {unlockedAchievements.length} / {achievements.length} desbloqueados
              </span>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="pt-6">
          {/* Category Filter */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {categories.map(category => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
                  selectedCategory === category
                    ? "bg-purple-500 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                )}
              >
                {category === 'all' ? 'Todos' : category}
              </button>
            ))}
          </div>

          {/* Achievements Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredAchievements.map(achievement => (
              <AchievementItem key={achievement.id} achievement={achievement} />
            ))}
          </div>

          {/* Stats Summary */}
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-gray-100">
            {Object.entries(rarityConfig).map(([rarity, config]) => {
              const count = unlockedAchievements.filter(a => a.rarity === rarity).length
              const total = achievements.filter(a => a.rarity === rarity).length
              
              return (
                <div key={rarity} className="text-center">
                  <div className={cn(
                    "inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium mb-2",
                    `bg-${config.color}-100 text-${config.color}-700`
                  )}>
                    {Array.from({ length: config.stars }).map((_, i) => (
                      <Star key={i} className="w-3 h-3 fill-current" />
                    ))}
                  </div>
                  <p className="text-lg font-bold text-gray-900">{count}/{total}</p>
                  <p className="text-xs text-gray-500 capitalize">{rarity}</p>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Milestones Section */}
      <Card>
        <CardHeader className="border-b border-gray-100">
          <CardTitle className="text-xl font-bold text-navy-700">
            Hitos Importantes
          </CardTitle>
        </CardHeader>
        
        <CardContent className="pt-6">
          {milestones.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              Aún no has alcanzado ningún hito. ¡Sigue trabajando!
            </p>
          ) : (
            <div className="space-y-4">
              {milestones.map(milestone => (
                <MilestoneItem key={milestone.id} milestone={milestone} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}