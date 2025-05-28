'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Avatar, AvatarFallback } from '@/components/ui/Avatar'
import { ChatMessage } from '@/components/chat/ChatMessage'
import { ChatSuggestions } from '@/components/chat/ChatSuggestions'
import { ChatInput } from '@/components/chat/ChatInput'
import { useAuth } from '@/contexts/AuthContext'
import { UploadResponse } from '@/services/upload'

export default function ChatPage() {
  const { user } = useAuth()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const {
    messages,
    isConnected,
    isTyping,
    isStreaming,
    error,
    sendMessage,
    sendTypingIndicator,
  } = useChat({
    onMessage: () => scrollToBottom(),
  })

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = (content: string, attachments?: UploadResponse[]) => {
    if (content.trim() || attachments?.length) {
      sendMessage(content, attachments)
      setInput('')
    }
  }

  const getAgentInfo = (agentId?: string) => {
    const agents = {
      'orchestrator': { name: 'Orchestrator', icon: '🎯', color: 'primary' },
      'elite_training_strategist': { name: 'Training Strategist', icon: '💪', color: 'blue' },
      'precision_nutrition_architect': { name: 'Nutrition Architect', icon: '🥗', color: 'green' },
      'biometrics_insight_engine': { name: 'Biometrics Engine', icon: '📊', color: 'purple' },
      'motivation_behavior_coach': { name: 'Motivation Coach', icon: '🧠', color: 'yellow' },
      'progress_tracker': { name: 'Progress Tracker', icon: '📈', color: 'indigo' },
    }
    return agents[agentId || 'orchestrator'] || agents['orchestrator']
  }

  return (
    <div className="container mx-auto px-4 py-6 h-[calc(100vh-4rem)]">
      <div className="flex flex-col h-full max-w-5xl mx-auto">
        {/* Chat Header */}
        <Card className="mb-4">
          <div className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center">
                  <Bot className="h-6 w-6 text-white" />
                </div>
                {isConnected && (
                  <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
                )}
              </div>
              <div>
                <h2 className="text-lg font-semibold">NGX Fitness Coach</h2>
                <p className="text-sm text-gray-500">
                  {isConnected ? 'Online' : 'Connecting...'}
                  {isTyping && ' • Typing...'}
                </p>
              </div>
            </div>
            <Badge variant={isConnected ? 'success' : 'secondary'}>
              {isConnected ? 'Connected' : 'Offline'}
            </Badge>
          </div>
        </Card>

        {/* Messages Area */}
        <Card className="flex-1 overflow-hidden">
          <div className="h-full overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <ChatSuggestions onSelect={(suggestion) => {
                setInput(suggestion)
              }} />
            )}

            <AnimatePresence>
              {messages.map((message, _index) => {
                const agent = getAgentInfo(message.agent_id)
                const isUser = message.role === 'user'

                return (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    isUser={isUser}
                    agentInfo={agent}
                    userAvatar={user?.avatar_url}
                    userName={user?.name}
                    onRegenerate={() => {
                      // TODO: Implement regenerate
                      console.log('Regenerate message:', message.id)
                    }}
                    onFeedback={(messageId, feedback) => {
                      // TODO: Implement feedback
                      console.log('Feedback:', messageId, feedback)
                    }}
                  />
                )
              })}
            </AnimatePresence>

            {isTyping && !isStreaming && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-3"
              >
                <Avatar size="sm">
                  <AvatarFallback>🎯</AvatarFallback>
                </Avatar>
                <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-4 py-3">
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </motion.div>
            )}

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-2"
              >
                <p className="text-sm text-destructive">
                  {error.message || 'Something went wrong'}
                </p>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </Card>

        {/* Input Area */}
        <Card className="mt-4">
          <ChatInput
            value={input}
            onChange={setInput}
            onSubmit={handleSendMessage}
            onTyping={sendTypingIndicator}
            disabled={!isConnected || isStreaming}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
          />
        </Card>
      </div>
    </div>
  )
}