'use client'

import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Filter, X } from 'lucide-react'
import { Agent } from '@/types'
import { AgentCard } from './AgentCard'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { agentsService } from '@/services/agents'

interface AgentSelectorProps {
  agents: Agent[]
  selectedAgents?: string[]
  onSelectAgent?: (agent: Agent) => void
  onDeselectAgent?: (agentId: string) => void
  multiSelect?: boolean
  showCategories?: boolean
}

export function AgentSelector({
  agents,
  selectedAgents = [],
  onSelectAgent,
  onDeselectAgent,
  multiSelect = true,
  showCategories = true,
}: AgentSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(agents.map(agent => agentsService.getCategoryForAgent(agent.id)))
    return Array.from(cats).sort()
  }, [agents])

  // Filter agents
  const filteredAgents = useMemo(() => {
    let filtered = agents

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(agent =>
        agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.capabilities.some(cap => 
          cap.toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    }

    // Filter by category
    if (selectedCategory) {
      filtered = filtered.filter(agent => 
        agentsService.getCategoryForAgent(agent.id) === selectedCategory
      )
    }

    return filtered
  }, [agents, searchQuery, selectedCategory])

  const handleSelectAgent = (agent: Agent) => {
    if (selectedAgents.includes(agent.id)) {
      onDeselectAgent?.(agent.id)
    } else {
      if (!multiSelect && selectedAgents.length > 0) {
        // Deselect all others in single select mode
        selectedAgents.forEach(id => onDeselectAgent?.(id))
      }
      onSelectAgent?.(agent)
    }
  }

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedCategory(null)
  }

  return (
    <div className="space-y-6">
      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search agents by name, description, or capabilities..."
            className="pl-10 pr-10"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {showCategories && (
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="h-4 w-4 text-gray-400" />
            <Button
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              All
            </Button>
            {categories.map(category => (
              <Button
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(
                  selectedCategory === category ? null : category
                )}
              >
                {category}
              </Button>
            ))}
          </div>
        )}

        {(searchQuery || selectedCategory) && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Found {filteredAgents.length} agent{filteredAgents.length !== 1 ? 's' : ''}
            </p>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
            >
              Clear filters
            </Button>
          </div>
        )}
      </div>

      {/* Selected Agents Summary */}
      {selectedAgents.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-primary/5 border border-primary/20 rounded-lg p-4"
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium">
              {selectedAgents.length} agent{selectedAgents.length !== 1 ? 's' : ''} selected
            </p>
            {multiSelect && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => selectedAgents.forEach(id => onDeselectAgent?.(id))}
              >
                Clear all
              </Button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedAgents.map(agentId => {
              const agent = agents.find(a => a.id === agentId)
              if (!agent) return null
              return (
                <Badge
                  key={agentId}
                  variant="secondary"
                  className="pl-2 pr-1 py-1"
                >
                  <span className="mr-1">{agent.icon}</span>
                  <span>{agent.name}</span>
                  <button
                    onClick={() => onDeselectAgent?.(agentId)}
                    className="ml-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* Agents Grid */}
      <AnimatePresence mode="popLayout">
        {filteredAgents.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center py-12"
          >
            <p className="text-muted-foreground">No agents found matching your criteria</p>
          </motion.div>
        ) : (
          <motion.div
            layout
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {filteredAgents.map(agent => (
              <motion.div
                key={agent.id}
                layout
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.2 }}
              >
                <AgentCard
                  agent={agent}
                  isSelected={selectedAgents.includes(agent.id)}
                  onSelect={handleSelectAgent}
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}