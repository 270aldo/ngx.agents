import { EventEmitter } from 'events'

export interface SSEMessage {
  id?: string
  event?: string
  data: string
  retry?: number
}

export class SSEClient extends EventEmitter {
  private eventSource: EventSource | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(url: string) {
    super()
    this.url = url
  }

  connect(token?: string) {
    const urlWithAuth = token ? `${this.url}?token=${token}` : this.url
    
    try {
      this.eventSource = new EventSource(urlWithAuth)
      
      this.eventSource.onopen = () => {
        console.log('SSE connected')
        this.reconnectAttempts = 0
        this.emit('connected')
      }

      this.eventSource.onerror = (error) => {
        console.error('SSE error:', error)
        this.emit('error', error)
        
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          this.handleReconnect()
        }
      }

      // Handle named events
      this.eventSource.addEventListener('message', (event) => {
        this.handleMessage('message', event.data)
      })

      this.eventSource.addEventListener('stream_start', (event) => {
        this.handleMessage('stream_start', event.data)
      })

      this.eventSource.addEventListener('stream_chunk', (event) => {
        this.handleMessage('stream_chunk', event.data)
      })

      this.eventSource.addEventListener('stream_end', (event) => {
        this.handleMessage('stream_end', event.data)
      })

      this.eventSource.addEventListener('error', (event) => {
        this.handleMessage('error', event.data)
      })

      this.eventSource.addEventListener('status', (event) => {
        this.handleMessage('status', event.data)
      })
    } catch (error) {
      console.error('Failed to create EventSource:', error)
      this.emit('error', error)
    }
  }

  private handleMessage(event: string, data: string) {
    try {
      const parsedData = JSON.parse(data)
      this.emit(event, parsedData)
    } catch (_error) {
      // If parsing fails, emit raw data
      this.emit(event, data)
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      
      console.log(`Reconnecting SSE in ${delay}ms (attempt ${this.reconnectAttempts})`)
      
      setTimeout(() => {
        this.connect()
      }, delay)
    } else {
      this.emit('reconnect_failed')
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
      this.emit('disconnected')
    }
  }

  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN
  }
}

// Hook for streaming chat responses
export function useChatStream(url: string) {
  const sseClient = new SSEClient(url)
  
  const streamChat = async (message: string, token?: string) => {
    return new Promise((resolve, reject) => {
      let fullResponse = ''
      let messageId: string | null = null
      
      sseClient.on('stream_start', (data) => {
        messageId = data.id
        sseClient.emit('start', data)
      })
      
      sseClient.on('stream_chunk', (data) => {
        fullResponse += data.content
        sseClient.emit('chunk', data)
      })
      
      sseClient.on('stream_end', (data) => {
        sseClient.disconnect()
        resolve({
          id: messageId || data.id,
          content: fullResponse,
          metadata: data.metadata,
        })
      })
      
      sseClient.on('error', (error) => {
        sseClient.disconnect()
        reject(error)
      })
      
      // Connect and send message
      sseClient.connect(token)
      
      // Send the message via POST to initiate streaming
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
        },
        body: JSON.stringify({ content: message }),
      }).catch(reject)
    })
  }
  
  return { streamChat, sseClient }
}