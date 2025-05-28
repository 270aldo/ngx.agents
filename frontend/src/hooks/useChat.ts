import { useState, useEffect, useCallback, useRef } from 'react'
import { wsService, WebSocketMessage } from '@/services/websocket'
import { Message } from '@/types'
import { api } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'

interface UseChatOptions {
  sessionId?: string
  onMessage?: (message: Message) => void
  onTyping?: (isTyping: boolean) => void
  onError?: (error: Error) => void
}

export function useChat(options: UseChatOptions = {}) {
  const { user } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const streamingMessageRef = useRef<Message | null>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!user) return

    // Load chat history
    loadChatHistory()

    // Connect WebSocket
    const token = localStorage.getItem('auth_token')
    if (token) {
      wsService.connect(token)
    }

    // Set up event listeners
    wsService.on('connected', handleConnected)
    wsService.on('disconnected', handleDisconnected)
    wsService.on('message', handleMessage)
    wsService.on('error', handleError)
    wsService.on('reconnect_failed', handleReconnectFailed)

    return () => {
      wsService.off('connected', handleConnected)
      wsService.off('disconnected', handleDisconnected)
      wsService.off('message', handleMessage)
      wsService.off('error', handleError)
      wsService.off('reconnect_failed', handleReconnectFailed)
      wsService.disconnect()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, options.sessionId])

  const loadChatHistory = async () => {
    try {
      const response = await api.get<Message[]>(`/chat/history${options.sessionId ? `?session_id=${options.sessionId}` : ''}`)
      if (response.data) {
        setMessages(response.data)
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const handleConnected = () => {
    setIsConnected(true)
    setError(null)
  }

  const handleDisconnected = () => {
    setIsConnected(false)
  }

  const handleMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'message':
        const newMessage: Message = {
          id: message.data.id || Date.now().toString(),
          content: message.data.content,
          role: message.data.role || 'assistant',
          agent_id: message.data.agent_id,
          created_at: message.timestamp,
          metadata: message.data.metadata,
        }
        setMessages(prev => [...prev, newMessage])
        setIsTyping(false)
        options.onMessage?.(newMessage)
        break

      case 'typing':
        setIsTyping(message.data.isTyping)
        options.onTyping?.(message.data.isTyping)
        break

      case 'stream_start':
        setIsStreaming(true)
        streamingMessageRef.current = {
          id: message.data.id || Date.now().toString(),
          content: '',
          role: 'assistant',
          agent_id: message.data.agent_id,
          created_at: message.timestamp,
          metadata: message.data.metadata,
        }
        setMessages(prev => [...prev, streamingMessageRef.current!])
        break

      case 'stream_chunk':
        if (streamingMessageRef.current) {
          streamingMessageRef.current.content += message.data.content
          setMessages(prev => {
            const newMessages = [...prev]
            const lastIndex = newMessages.length - 1
            if (lastIndex >= 0 && newMessages[lastIndex].id === streamingMessageRef.current!.id) {
              newMessages[lastIndex] = { ...streamingMessageRef.current! }
            }
            return newMessages
          })
        }
        break

      case 'stream_end':
        setIsStreaming(false)
        streamingMessageRef.current = null
        setIsTyping(false)
        break

      case 'error':
        const errorMessage = new Error(message.data.message || 'An error occurred')
        setError(errorMessage)
        options.onError?.(errorMessage)
        break
    }
  }

  const handleError = (error: Error) => {
    setError(error)
    options.onError?.(error)
  }

  const handleReconnectFailed = () => {
    setError(new Error('Failed to reconnect to chat service'))
  }

  const sendMessage = useCallback(async (content: string, attachments?: unknown[]) => {
    if (!content.trim()) return

    // Add user message immediately
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      created_at: new Date().toISOString(),
      metadata: attachments ? { attachments } : undefined,
    }
    setMessages(prev => [...prev, userMessage])

    // Send via WebSocket if connected, otherwise use HTTP
    if (wsService.isConnected()) {
      wsService.sendMessage(content, { attachments })
    } else {
      try {
        const response = await api.post<Message>('/chat/message', {
          content,
          session_id: options.sessionId,
          attachments,
        })
        if (response.data) {
          setMessages(prev => [...prev, response.data!])
        }
      } catch (error) {
        console.error('Failed to send message:', error)
        setError(error as Error)
      }
    }

    // Simulate typing indicator
    setIsTyping(true)
  }, [options.sessionId])

  const sendTypingIndicator = useCallback((isTyping: boolean) => {
    if (wsService.isConnected()) {
      wsService.sendTyping(isTyping)
    }

    // Auto-stop typing after 5 seconds
    if (isTyping) {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current)
      }
      typingTimeoutRef.current = setTimeout(() => {
        wsService.sendTyping(false)
      }, 5000)
    } else {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current)
        typingTimeoutRef.current = null
      }
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    isConnected,
    isTyping,
    isStreaming,
    error,
    sendMessage,
    sendTypingIndicator,
    clearMessages,
  }
}