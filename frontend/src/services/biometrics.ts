import { EventEmitter } from 'events'
import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { BiometricData } from '@/types'

interface BiometricUpdate {
  type: 'heart_rate' | 'steps' | 'calories' | 'sleep' | 'weight' | 'body_fat' | 'activity' | 'recovery'
  data: BiometricData
  timestamp: string
}

class BiometricsService extends EventEmitter {
  private ws: WebSocket | null = null
  private pollingInterval: NodeJS.Timeout | null = null
  private isConnected = false

  connect(token: string) {
    // WebSocket for real-time updates
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/biometrics?token=${token}`
    
    try {
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log('Biometrics WebSocket connected')
        this.isConnected = true
        this.emit('connected')
      }

      this.ws.onmessage = (event) => {
        try {
          const update: BiometricUpdate = JSON.parse(event.data)
          this.emit('update', update)
          this.emit(update.type, update.data)
        } catch (error) {
          console.error('Failed to parse biometric update:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('Biometrics WebSocket error:', error)
        this.emit('error', error)
      }

      this.ws.onclose = () => {
        console.log('Biometrics WebSocket disconnected')
        this.isConnected = false
        this.emit('disconnected')
        
        // Fallback to polling if WebSocket fails
        this.startPolling()
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      this.startPolling()
    }
  }

  private startPolling() {
    if (this.pollingInterval) return
    
    // Poll every 30 seconds for updates
    this.pollingInterval = setInterval(async () => {
      try {
        const response = await api.get<BiometricData[]>('/biometrics/latest')
        if (response.data) {
          response.data.forEach(data => {
            this.emit('update', {
              type: data.type,
              data,
              timestamp: new Date().toISOString(),
            })
          })
        }
      } catch (error) {
        console.error('Failed to poll biometric data:', error)
      }
    }, 30000)
  }

  async fetchHistoricalData(
    type: string,
    startDate: Date,
    endDate: Date
  ): Promise<BiometricData[]> {
    try {
      const response = await api.get<BiometricData[]>('/biometrics/history', {
        params: {
          type,
          start_date: startDate.toISOString(),
          end_date: endDate.toISOString(),
        },
      })
      return response.data || []
    } catch (error) {
      console.error('Failed to fetch historical data:', error)
      return []
    }
  }

  async fetchLatestMetrics(): Promise<Record<string, BiometricData>> {
    try {
      const response = await api.get<Record<string, BiometricData>>('/biometrics/summary')
      return response.data || {}
    } catch (error) {
      console.error('Failed to fetch latest metrics:', error)
      return {}
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval)
      this.pollingInterval = null
    }
    
    this.isConnected = false
    this.removeAllListeners()
  }

  getConnectionStatus(): boolean {
    return this.isConnected
  }
}

export const biometricsService = new BiometricsService()

// Hook for using biometrics data
export function useBiometrics() {
  const [metrics, setMetrics] = useState<Record<string, BiometricData>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) return

    // Connect to real-time updates
    biometricsService.connect(token)

    // Load initial data
    loadInitialData()

    // Set up event listeners
    biometricsService.on('update', handleUpdate)
    biometricsService.on('error', handleError)

    return () => {
      biometricsService.off('update', handleUpdate)
      biometricsService.off('error', handleError)
      biometricsService.disconnect()
    }
  }, [])

  const loadInitialData = async () => {
    try {
      const data = await biometricsService.fetchLatestMetrics()
      setMetrics(data)
    } catch (err) {
      setError(err as Error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = (update: BiometricUpdate) => {
    setMetrics(prev => ({
      ...prev,
      [update.type]: update.data,
    }))
  }

  const handleError = (err: Error) => {
    setError(err)
  }

  return { metrics, loading, error }
}