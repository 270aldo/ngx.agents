import { motion } from 'framer-motion'
import { Copy, Check, RotateCcw, ThumbsUp, ThumbsDown, Paperclip } from 'lucide-react'
import { useState } from 'react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import { VoiceFeedback } from './VoiceFeedback'
import { cn } from '@/utils/cn'
import { Message } from '@/types'

interface ChatMessageProps {
  message: Message
  isUser: boolean
  agentInfo: {
    name: string
    icon: string
    color: string
  }
  userAvatar?: string
  userName?: string
  onRegenerate?: () => void
  onFeedback?: (messageId: string, feedback: 'positive' | 'negative') => void
}

export function ChatMessage({
  message,
  isUser,
  agentInfo,
  userAvatar,
  userName,
  onRegenerate,
  onFeedback,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleFeedback = (type: 'positive' | 'negative') => {
    setFeedback(type)
    onFeedback?.(message.id, type)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}
    >
      {!isUser && (
        <Avatar size="sm" className="mt-1">
          <AvatarFallback className={cn(
            'text-lg',
            agentInfo.color === 'primary' && 'bg-primary/20 text-primary',
            agentInfo.color === 'blue' && 'bg-blue-500/20 text-blue-500',
            agentInfo.color === 'green' && 'bg-green-500/20 text-green-500',
            agentInfo.color === 'purple' && 'bg-purple-500/20 text-purple-500',
            agentInfo.color === 'yellow' && 'bg-yellow-500/20 text-yellow-500',
            agentInfo.color === 'indigo' && 'bg-indigo-500/20 text-indigo-500'
          )}>
            {agentInfo.icon}
          </AvatarFallback>
        </Avatar>
      )}

      <div className={cn('max-w-[70%] space-y-1', isUser ? 'items-end' : 'items-start')}>
        {!isUser && message.agent_id && (
          <p className="text-xs text-gray-500 px-1">{agentInfo.name}</p>
        )}
        
        <div className={cn('group relative')}>
          <div
            className={cn(
              'rounded-2xl px-4 py-3',
              isUser
                ? 'bg-primary text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
            )}
          >
            {/* Message content with markdown support */}
            <div className="text-sm whitespace-pre-wrap break-words">
              {message.content.split('\n').map((line, i) => {
                // Simple markdown parsing for code blocks
                if (line.startsWith('```')) {
                  return (
                    <pre key={i} className="bg-black/20 rounded p-2 my-2 overflow-x-auto">
                      <code className="text-xs">{line.replace(/```/g, '')}</code>
                    </pre>
                  )
                }
                // Bold text
                if (line.includes('**')) {
                  return (
                    <p key={i}>
                      {line.split('**').map((part, j) => 
                        j % 2 === 1 ? <strong key={j}>{part}</strong> : part
                      )}
                    </p>
                  )
                }
                return <p key={i}>{line}</p>
              })}
            </div>

            {/* Attachments */}
            {message.metadata?.attachments && message.metadata.attachments.length > 0 && (
              <div className="mt-2 space-y-1">
                {message.metadata.attachments.map((attachment, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 text-xs opacity-70"
                  >
                    <Paperclip className="h-3 w-3" />
                    <span>{attachment.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action buttons for assistant messages */}
          {!isUser && (
            <div className="absolute -bottom-8 left-0 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
              <VoiceFeedback 
                text={message.content}
                className="h-7 w-7"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="h-7 px-2"
              >
                {copied ? (
                  <Check className="h-3 w-3" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
              
              {onRegenerate && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onRegenerate}
                  className="h-7 px-2"
                >
                  <RotateCcw className="h-3 w-3" />
                </Button>
              )}
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleFeedback('positive')}
                className={cn(
                  'h-7 px-2',
                  feedback === 'positive' && 'text-green-500'
                )}
              >
                <ThumbsUp className="h-3 w-3" />
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleFeedback('negative')}
                className={cn(
                  'h-7 px-2',
                  feedback === 'negative' && 'text-red-500'
                )}
              >
                <ThumbsDown className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-400 px-1">
          {new Date(message.created_at).toLocaleTimeString()}
          {message.metadata?.processing_time && (
            <span className="ml-2">
              • {(message.metadata.processing_time / 1000).toFixed(1)}s
            </span>
          )}
        </p>
      </div>

      {isUser && (
        <Avatar size="sm" className="mt-1">
          <AvatarImage src={userAvatar} />
          <AvatarFallback>
            {userName?.split(' ').map(n => n[0]).join('') || 'U'}
          </AvatarFallback>
        </Avatar>
      )}
    </motion.div>
  )
}