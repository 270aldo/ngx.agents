'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import voiceService from '@/services/voice'
import { toast } from 'react-hot-toast'
import { 
  Mic, 
  Volume2,
  HelpCircle,
  Command
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/cn'
import { motion, AnimatePresence } from 'framer-motion'

interface VoiceCommandsProps {
  enabled?: boolean
  onCommand?: (command: string, action: string, params?: unknown) => void
  className?: string
}

export function VoiceCommands({ 
  enabled = true, 
  onCommand,
  className 
}: VoiceCommandsProps) {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [showHelp, setShowHelp] = useState(false)
  const router = useRouter()

  const commands = [
    { text: 'Muestra mi progreso', action: 'navigate', path: '/progress' },
    { text: 'Abre dashboard', action: 'navigate', path: '/dashboard' },
    { text: 'Busca agentes', action: 'navigate', path: '/agents' },
    { text: 'Registra mi peso', action: 'log', type: 'weight' },
    { text: 'Analiza mi entrenamiento', action: 'analyze', type: 'workout' },
    { text: 'Crea plan de nutrición', action: 'create', type: 'nutrition' },
    { text: 'Ayuda', action: 'help' },
    { text: 'Cancelar', action: 'cancel' }
  ]

  useEffect(() => {
    if (!enabled || !voiceService.isSpeechRecognitionSupported()) return

    // Set up keyboard shortcut (Ctrl/Cmd + Shift + M)
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'M') {
        e.preventDefault()
        toggleListening()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enabled])

  const toggleListening = () => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  const startListening = () => {
    if (!voiceService.isSpeechRecognitionSupported()) {
      toast.error('Voice commands not supported in your browser')
      return
    }

    setIsListening(true)
    setTranscript('')

    voiceService.startSpeechRecognition(
      (text, isFinal) => {
        setTranscript(text)
        
        if (isFinal) {
          const command = voiceService.parseVoiceCommand(text.toLowerCase())
          if (command) {
            handleCommand(command.action, command.parameters)
          } else {
            // If no specific command matched, treat as general query
            onCommand?.(text, 'query', { text })
          }
          
          setTimeout(() => {
            setTranscript('')
            stopListening()
          }, 1000)
        }
      },
      (error) => {
        toast.error('Voice recognition error')
        stopListening()
      }
    )

    toast.success('Listening for commands...')
  }

  const stopListening = () => {
    voiceService.stopSpeechRecognition()
    setIsListening(false)
    setTranscript('')
  }

  const handleCommand = async (action: string, params?: any) => {
    switch (action) {
      case 'navigate':
        const navCommand = commands.find(c => c.action === 'navigate' && transcript.toLowerCase().includes(c.text.toLowerCase()))
        if (navCommand && 'path' in navCommand) {
          router.push(navCommand.path)
          toast.success(`Navigating to ${navCommand.path}`)
        }
        break

      case 'log':
        onCommand?.('log', action, params)
        toast.success('Opening log entry...')
        break

      case 'analyze':
        onCommand?.('analyze', action, params)
        toast.success('Starting analysis...')
        break

      case 'create':
        onCommand?.('create', action, params)
        toast.success('Creating new plan...')
        break

      case 'help':
        setShowHelp(true)
        await voiceService.textToSpeech('Puedes decirme comandos como: muestra mi progreso, abre dashboard, registra mi peso, o analiza mi entrenamiento.')
        break

      case 'cancel':
        stopListening()
        toast.success('Command cancelled')
        break

      default:
        onCommand?.(transcript, action, params)
    }
  }

  if (!enabled || !voiceService.isSpeechRecognitionSupported()) {
    return null
  }

  return (
    <>
      <div className={cn("relative", className)}>
        <Button
          variant={isListening ? "default" : "outline"}
          size="icon"
          onClick={toggleListening}
          title="Voice commands (Ctrl+Shift+M)"
        >
          {isListening ? (
            <Mic className="w-4 h-4" />
          ) : (
            <MicOff className="w-4 h-4" />
          )}
        </Button>

        {/* Listening indicator */}
        <AnimatePresence>
          {isListening && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute -top-2 -right-2"
            >
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Transcript preview */}
        <AnimatePresence>
          {isListening && transcript && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full mt-2 right-0 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 min-w-[200px] max-w-[300px] z-50"
            >
              <div className="flex items-start gap-2">
                <Volume2 className="w-4 h-4 text-purple-500 mt-0.5" />
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  "{transcript}"
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Help Modal */}
      <AnimatePresence>
        {showHelp && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowHelp(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                  <Command className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="text-lg font-semibold">Voice Commands</h3>
              </div>

              <div className="space-y-3 mb-6">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Use voice commands to navigate and control the app. Say:
                </p>
                
                <div className="space-y-2">
                  {commands.map((cmd, index) => (
                    <div 
                      key={index}
                      className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg"
                    >
                      <Mic className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-medium">"{cmd.text}"</span>
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-2 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <HelpCircle className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  <p className="text-sm text-purple-700 dark:text-purple-300">
                    Press <kbd className="px-1.5 py-0.5 bg-white dark:bg-gray-700 rounded text-xs font-mono">Ctrl+Shift+M</kbd> to toggle voice commands
                  </p>
                </div>
              </div>

              <Button
                onClick={() => setShowHelp(false)}
                className="w-full"
              >
                Got it
              </Button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}