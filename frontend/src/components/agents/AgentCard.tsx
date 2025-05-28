import { motion } from 'framer-motion'
import { Check, Loader2, Sparkles, Power } from 'lucide-react'
import { Agent } from '@/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/cn'
import { agentsService } from '@/services/agents'

interface AgentCardProps {
  agent: Agent
  isSelected?: boolean
  isLoading?: boolean
  onSelect?: (agent: Agent) => void
  onToggleStatus?: (agent: Agent) => void
  showDetails?: boolean
}

export function AgentCard({
  agent,
  isSelected = false,
  isLoading = false,
  onSelect,
  onToggleStatus,
  showDetails = true,
}: AgentCardProps) {
  const category = agentsService.getCategoryForAgent(agent.id)
  const categoryColor = agentsService.getColorForCategory(category)

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'busy':
        return 'warning'
      case 'inactive':
        return 'secondary'
      default:
        return 'secondary'
    }
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      <Card
        className={cn(
          'relative cursor-pointer transition-all duration-200',
          isSelected && 'ring-2 ring-primary',
          agent.status === 'inactive' && 'opacity-60'
        )}
        onClick={() => onSelect?.(agent)}
      >
        {/* Selection indicator */}
        {isSelected && (
          <div className="absolute -top-2 -right-2 z-10">
            <div className="bg-primary rounded-full p-1">
              <Check className="h-4 w-4 text-white" />
            </div>
          </div>
        )}

        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                'text-3xl rounded-lg p-2',
                categoryColor === 'primary' && 'bg-primary/10',
                categoryColor === 'blue' && 'bg-blue-500/10',
                categoryColor === 'green' && 'bg-green-500/10',
                categoryColor === 'red' && 'bg-red-500/10',
                categoryColor === 'purple' && 'bg-purple-500/10',
                categoryColor === 'yellow' && 'bg-yellow-500/10',
                categoryColor === 'gray' && 'bg-gray-500/10',
                categoryColor === 'orange' && 'bg-orange-500/10',
                categoryColor === 'pink' && 'bg-pink-500/10',
                categoryColor === 'indigo' && 'bg-indigo-500/10',
                categoryColor === 'teal' && 'bg-teal-500/10'
              )}>
                {agent.icon}
              </div>
              <div>
                <CardTitle className="text-lg">{agent.name}</CardTitle>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs">
                    {category}
                  </Badge>
                  <Badge variant={getStatusColor(agent.status)} className="text-xs">
                    {agent.status}
                  </Badge>
                </div>
              </div>
            </div>
            
            {onToggleStatus && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  e.stopPropagation()
                  onToggleStatus(agent)
                }}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Power className={cn(
                    'h-4 w-4',
                    agent.status === 'active' && 'text-green-500'
                  )} />
                )}
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent>
          <CardDescription className="text-sm mb-3">
            {agent.description}
          </CardDescription>

          {showDetails && agent.capabilities.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Capabilities:</p>
              <div className="flex flex-wrap gap-1">
                {agent.capabilities.slice(0, 3).map((capability, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="text-xs"
                  >
                    {capability}
                  </Badge>
                ))}
                {agent.capabilities.length > 3 && (
                  <Badge variant="secondary" className="text-xs">
                    +{agent.capabilities.length - 3} more
                  </Badge>
                )}
              </div>
            </div>
          )}

          {isSelected && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 pt-3 border-t"
            >
              <div className="flex items-center gap-2 text-sm text-primary">
                <Sparkles className="h-4 w-4" />
                <span>Active in current session</span>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}