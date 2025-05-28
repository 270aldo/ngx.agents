import { EventEmitter } from 'events'

export interface WebSocketMessage {
  type: 'message' | 'status' | 'error' | 'typing' | 'stream_start' | 'stream_chunk' | 'stream_end'
  data: unknown
  timestamp: string
}

class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null
  private reconnectTimeout: NodeJS.Timeout | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private url: string
  private token: string | null = null

  constructor() {
    super()
    this.url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
  }

  connect(token: string) {
    this.token = token
    this.connectWebSocket()
  }

  private connectWebSocket() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    const wsUrl = `${this.url}/ws/chat?token=${this.token}`
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this.emit('connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        this.emit('message', message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.emit('error', error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.emit('disconnected')
      this.handleReconnect()
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)
      
      this.reconnectTimeout = setTimeout(() => {
        this.connectWebSocket()
      }, delay)
    } else {
      this.emit('reconnect_failed')
    }
  }

  sendMessage(content: string, metadata?: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'message',
        content,
        metadata,
        timestamp: new Date().toISOString(),
      }
      this.ws.send(JSON.stringify(message))
    } else {
      console.error('WebSocket is not connected')
      this.emit('error', new Error('WebSocket is not connected'))
    }
  }

  sendTyping(isTyping: boolean) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'typing',
        isTyping,
        timestamp: new Date().toISOString(),
      }
      this.ws.send(JSON.stringify(message))
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsService = new WebSocketService()