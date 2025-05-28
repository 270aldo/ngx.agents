import { api } from '@/lib/api'
import { Agent } from '@/types'

export const AGENTS_DATA: Record<string, Agent> = {
  orchestrator: {
    id: 'orchestrator',
    name: 'Orchestrator',
    description: 'Central AI coordinator that analyzes your needs and routes to specialized agents',
    icon: '🎯',
    capabilities: [
      'Intent analysis and routing',
      'Multi-agent coordination',
      'Context management',
      'Response synthesis',
    ],
    status: 'active',
  },
  elite_training_strategist: {
    id: 'elite_training_strategist',
    name: 'Elite Training Strategist',
    description: 'Designs personalized workout programs tailored to your fitness goals',
    icon: '💪',
    capabilities: [
      'Custom workout plans',
      'Exercise form analysis',
      'Progressive overload tracking',
      'Injury prevention strategies',
    ],
    status: 'active',
  },
  precision_nutrition_architect: {
    id: 'precision_nutrition_architect',
    name: 'Precision Nutrition Architect',
    description: 'Creates customized meal plans based on your nutritional needs',
    icon: '🥗',
    capabilities: [
      'Personalized meal planning',
      'Macro/micro nutrient tracking',
      'Recipe recommendations',
      'Dietary restriction support',
    ],
    status: 'active',
  },
  biometrics_insight_engine: {
    id: 'biometrics_insight_engine',
    name: 'Biometrics Insight Engine',
    description: 'Analyzes health data to provide actionable insights',
    icon: '📊',
    capabilities: [
      'Real-time health monitoring',
      'Trend analysis',
      'Anomaly detection',
      'Predictive health insights',
    ],
    status: 'active',
  },
  motivation_behavior_coach: {
    id: 'motivation_behavior_coach',
    name: 'Motivation Behavior Coach',
    description: 'Provides psychological support and behavior change strategies',
    icon: '🧠',
    capabilities: [
      'Goal setting and tracking',
      'Habit formation',
      'Motivational messaging',
      'Behavioral psychology techniques',
    ],
    status: 'active',
  },
  progress_tracker: {
    id: 'progress_tracker',
    name: 'Progress Tracker',
    description: 'Monitors and visualizes your fitness journey progress',
    icon: '📈',
    capabilities: [
      'Performance metrics tracking',
      'Progress visualization',
      'Goal achievement analysis',
      'Milestone celebrations',
    ],
    status: 'active',
  },
  recovery_corrective: {
    id: 'recovery_corrective',
    name: 'Recovery Corrective',
    description: 'Specializes in recovery optimization and injury prevention',
    icon: '🔄',
    capabilities: [
      'Recovery protocol design',
      'Injury risk assessment',
      'Mobility exercises',
      'Sleep optimization',
    ],
    status: 'active',
  },
  security_compliance_guardian: {
    id: 'security_compliance_guardian',
    name: 'Security Compliance Guardian',
    description: 'Ensures data privacy and security compliance',
    icon: '🔒',
    capabilities: [
      'Data encryption',
      'Privacy protection',
      'HIPAA compliance',
      'Secure data handling',
    ],
    status: 'active',
  },
  systems_integration_ops: {
    id: 'systems_integration_ops',
    name: 'Systems Integration Ops',
    description: 'Manages integrations with external devices and platforms',
    icon: '🔧',
    capabilities: [
      'Device connectivity',
      'API integrations',
      'Data synchronization',
      'Platform compatibility',
    ],
    status: 'active',
  },
  biohacking_innovator: {
    id: 'biohacking_innovator',
    name: 'Biohacking Innovator',
    description: 'Explores cutting-edge optimization techniques',
    icon: '🧬',
    capabilities: [
      'Advanced optimization strategies',
      'Supplement recommendations',
      'Biohacking protocols',
      'Performance enhancement',
    ],
    status: 'active',
  },
  client_success_liaison: {
    id: 'client_success_liaison',
    name: 'Client Success Liaison',
    description: 'Ensures optimal user experience and satisfaction',
    icon: '🤝',
    capabilities: [
      'User onboarding',
      'Support and guidance',
      'Feedback collection',
      'Experience optimization',
    ],
    status: 'active',
  },
}

class AgentsService {
  async getAllAgents(): Promise<Agent[]> {
    try {
      const response = await api.get<Agent[]>('/agents')
      return response.data || Object.values(AGENTS_DATA)
    } catch (error) {
      console.error('Failed to fetch agents:', error)
      // Return static data as fallback
      return Object.values(AGENTS_DATA)
    }
  }

  async getAgent(agentId: string): Promise<Agent | null> {
    try {
      const response = await api.get<Agent>(`/agents/${agentId}`)
      return response.data || AGENTS_DATA[agentId] || null
    } catch (error) {
      console.error('Failed to fetch agent:', error)
      return AGENTS_DATA[agentId] || null
    }
  }

  async getAgentStatus(agentId: string): Promise<'active' | 'inactive' | 'busy'> {
    try {
      const response = await api.get<{ status: Agent['status'] }>(`/agents/${agentId}/status`)
      return response.data?.status || 'inactive'
    } catch (error) {
      console.error('Failed to fetch agent status:', error)
      return 'inactive'
    }
  }

  async activateAgent(agentId: string): Promise<boolean> {
    try {
      const response = await api.post(`/agents/${agentId}/activate`)
      return response.status === 200
    } catch (error) {
      console.error('Failed to activate agent:', error)
      return false
    }
  }

  async deactivateAgent(agentId: string): Promise<boolean> {
    try {
      const response = await api.post(`/agents/${agentId}/deactivate`)
      return response.status === 200
    } catch (error) {
      console.error('Failed to deactivate agent:', error)
      return false
    }
  }

  getCategoryForAgent(agentId: string): string {
    const categories: Record<string, string> = {
      orchestrator: 'Core',
      elite_training_strategist: 'Fitness',
      precision_nutrition_architect: 'Nutrition',
      biometrics_insight_engine: 'Health',
      motivation_behavior_coach: 'Mental',
      progress_tracker: 'Analytics',
      recovery_corrective: 'Recovery',
      security_compliance_guardian: 'Security',
      systems_integration_ops: 'Technical',
      biohacking_innovator: 'Advanced',
      client_success_liaison: 'Support',
    }
    return categories[agentId] || 'Other'
  }

  getColorForCategory(category: string): string {
    const colors: Record<string, string> = {
      Core: 'primary',
      Fitness: 'blue',
      Nutrition: 'green',
      Health: 'red',
      Mental: 'purple',
      Analytics: 'indigo',
      Recovery: 'yellow',
      Security: 'gray',
      Technical: 'orange',
      Advanced: 'pink',
      Support: 'teal',
    }
    return colors[category] || 'gray'
  }
}

export const agentsService = new AgentsService()