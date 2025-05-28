import { api } from '@/lib/api'
import { Progress, Goal, ProgressStats, Milestone, Achievement } from '@/types'

class ProgressService {
  // Progress entries
  async getProgress(userId: string, params?: {
    start_date?: string
    end_date?: string
    limit?: number
  }) {
    const response = await api.get(`/progress/${userId}`, { params })
    return response.data
  }

  async getLatestProgress(userId: string) {
    const response = await api.get(`/progress/${userId}/latest`)
    return response.data
  }

  async createProgress(data: Partial<Progress>) {
    const response = await api.post('/progress', data)
    return response.data
  }

  async updateProgress(id: string, data: Partial<Progress>) {
    const response = await api.put(`/progress/${id}`, data)
    return response.data
  }

  async deleteProgress(id: string) {
    const response = await api.delete(`/progress/${id}`)
    return response.data
  }

  // Goals
  async getGoals(userId: string, status?: 'active' | 'completed' | 'paused' | 'failed') {
    const response = await api.get(`/goals/${userId}`, {
      params: { status }
    })
    return response.data
  }

  async createGoal(data: Partial<Goal>) {
    const response = await api.post('/goals', data)
    return response.data
  }

  async updateGoal(id: string, data: Partial<Goal>) {
    const response = await api.put(`/goals/${id}`, data)
    return response.data
  }

  async updateGoalProgress(id: string, currentValue: number) {
    const response = await api.patch(`/goals/${id}/progress`, { current_value: currentValue })
    return response.data
  }

  async deleteGoal(id: string) {
    const response = await api.delete(`/goals/${id}`)
    return response.data
  }

  // Achievements
  async getAchievements(userId: string, unlocked?: boolean) {
    const response = await api.get(`/achievements/${userId}`, {
      params: { unlocked }
    })
    return response.data
  }

  async unlockAchievement(userId: string, achievementId: string) {
    const response = await api.post(`/achievements/${userId}/unlock/${achievementId}`)
    return response.data
  }

  // Stats
  async getProgressStats(userId: string) {
    const response = await api.get<ProgressStats>(`/progress/${userId}/stats`)
    return response.data
  }

  // Milestones
  async getMilestones(userId: string) {
    const response = await api.get(`/milestones/${userId}`)
    return response.data
  }

  async createMilestone(data: Partial<Milestone>) {
    const response = await api.post('/milestones', data)
    return response.data
  }

  async celebrateMilestone(id: string) {
    const response = await api.patch(`/milestones/${id}/celebrate`)
    return response.data
  }

  // Photos
  async uploadProgressPhoto(file: File, metadata: {
    type: 'front' | 'side' | 'back'
    notes?: string
  }) {
    const formData = new FormData()
    formData.append('photo', file)
    formData.append('type', metadata.type)
    if (metadata.notes) {
      formData.append('notes', metadata.notes)
    }

    const response = await api.post('/progress/photos', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }

  async deleteProgressPhoto(id: string) {
    const response = await api.delete(`/progress/photos/${id}`)
    return response.data
  }

  // Comparison
  async getProgressComparison(userId: string, date1: string, date2: string) {
    const response = await api.get(`/progress/${userId}/compare`, {
      params: { date1, date2 }
    })
    return response.data
  }

  // Export
  async exportProgressReport(userId: string, format: 'pdf' | 'csv' = 'pdf') {
    const response = await api.get(`/progress/${userId}/export`, {
      params: { format },
      responseType: 'blob'
    })
    return response.data
  }
}

const progressService = new ProgressService()
export default progressService