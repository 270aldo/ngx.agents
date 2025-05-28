'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Bot, Sparkles, Settings, Plus, Users } from 'lucide-react'
import { agentsService, AGENTS_DATA } from '@/services/agents'
import { AgentSelector } from '@/components/agents/AgentSelector'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { Agent } from '@/types'
import { useRouter } from 'next/navigation'

export default function AgentsPage() {
  const router = useRouter()
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgents, setSelectedAgents] = useState<string[]>([])
  const [activeAgents, setActiveAgents] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [savingChanges, setSavingChanges] = useState(false)

  useEffect(() => {
    loadAgents()
  }, [])

  const loadAgents = async () => {
    try {
      const agentsList = await agentsService.getAllAgents()
      setAgents(agentsList)
      
      // Set initial active agents (those with 'active' status)
      const active = agentsList
        .filter(agent => agent.status === 'active')
        .map(agent => agent.id)
      setActiveAgents(active)
      setSelectedAgents(active)
    } catch (error) {
      console.error('Failed to load agents:', error)
      // Use static data as fallback
      setAgents(Object.values(AGENTS_DATA))
    } finally {
      setLoading(false)
    }
  }

  const handleSelectAgent = (agent: Agent) => {
    setSelectedAgents(prev => [...prev, agent.id])
  }

  const handleDeselectAgent = (agentId: string) => {
    setSelectedAgents(prev => prev.filter(id => id !== agentId))
  }

  const _handleToggleAgentStatus = async (agent: Agent) => {
    try {
      if (agent.status === 'active') {
        await agentsService.deactivateAgent(agent.id)
      } else {
        await agentsService.activateAgent(agent.id)
      }
      // Reload agents to get updated status
      await loadAgents()
    } catch (error) {
      console.error('Failed to toggle agent status:', error)
    }
  }

  const handleSaveChanges = async () => {
    setSavingChanges(true)
    try {
      // Activate selected agents
      for (const agentId of selectedAgents) {
        if (!activeAgents.includes(agentId)) {
          await agentsService.activateAgent(agentId)
        }
      }
      
      // Deactivate unselected agents
      for (const agentId of activeAgents) {
        if (!selectedAgents.includes(agentId)) {
          await agentsService.deactivateAgent(agentId)
        }
      }
      
      setActiveAgents(selectedAgents)
      // Show success message or redirect
      router.push('/chat')
    } catch (error) {
      console.error('Failed to save changes:', error)
    } finally {
      setSavingChanges(false)
    }
  }

  const featuredAgent = agents.find(a => a.id === 'orchestrator') || agents[0]

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-48" />
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
          <h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
            <Bot className="h-8 w-8 text-primary" />
            AI Agents
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage your team of specialized AI fitness coaches
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="px-3 py-1">
            <Users className="h-3 w-3 mr-1" />
            {selectedAgents.length} Active
          </Badge>
          <Button variant="outline" size="sm">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Featured Agent */}
      {featuredAgent && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Card className="bg-gradient-to-br from-primary/10 to-purple-600/10 border-primary/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  <CardTitle>Featured Agent</CardTitle>
                </div>
                <Badge variant="default">Core System</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="flex items-center gap-4 mb-4">
                    <div className="text-5xl">{featuredAgent.icon}</div>
                    <div>
                      <h3 className="text-2xl font-bold">{featuredAgent.name}</h3>
                      <p className="text-muted-foreground">{featuredAgent.description}</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Key Capabilities:</p>
                    <ul className="space-y-1">
                      {featuredAgent.capabilities.map((capability, index) => (
                        <li key={index} className="flex items-center gap-2 text-sm">
                          <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                          {capability}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="flex items-center justify-center">
                  <div className="relative">
                    <div className="absolute inset-0 bg-primary/20 blur-3xl" />
                    <div className="relative bg-gradient-to-br from-primary to-purple-600 text-white rounded-2xl p-6 text-center">
                      <div className="text-6xl mb-4">{featuredAgent.icon}</div>
                      <p className="text-lg font-medium">Always Active</p>
                      <p className="text-sm opacity-80">Central Intelligence System</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Agent Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Select Your AI Coaches</CardTitle>
          <CardDescription>
            Choose which specialized agents you want to work with. Each agent provides unique expertise to help you achieve your fitness goals.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AgentSelector
            agents={agents.filter(a => a.id !== 'orchestrator')} // Orchestrator is always active
            selectedAgents={selectedAgents.filter(id => id !== 'orchestrator')}
            onSelectAgent={handleSelectAgent}
            onDeselectAgent={handleDeselectAgent}
            multiSelect={true}
            showCategories={true}
          />
          
          {/* Save Changes */}
          <div className="mt-8 flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <div>
              <p className="font-medium">Ready to start?</p>
              <p className="text-sm text-muted-foreground">
                Your selected agents will be available in the chat interface
              </p>
            </div>
            <Button
              onClick={handleSaveChanges}
              disabled={savingChanges || selectedAgents.length === 0}
              className="min-w-[120px]"
            >
              {savingChanges ? (
                <>Saving...</>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Save & Continue
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Agents</p>
                <p className="text-2xl font-bold">{agents.length}</p>
              </div>
              <Bot className="h-8 w-8 text-primary opacity-20" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Agents</p>
                <p className="text-2xl font-bold">{selectedAgents.length}</p>
              </div>
              <Sparkles className="h-8 w-8 text-green-500 opacity-20" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Categories</p>
                <p className="text-2xl font-bold">
                  {new Set(agents.map(a => agentsService.getCategoryForAgent(a.id))).size}
                </p>
              </div>
              <Settings className="h-8 w-8 text-blue-500 opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}