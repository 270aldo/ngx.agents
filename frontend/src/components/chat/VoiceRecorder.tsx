'use client'

import { useState, useRef, useEffect } from 'react'
import { 
  Mic, 
  Square, 
  X,
  Volume2,
  AlertCircle
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/cn'
import { motion, AnimatePresence } from 'framer-motion'
import voiceService from '@/services/voice'
import { toast } from 'react-hot-toast'

interface VoiceRecorderProps {
  onTranscript: (text: string) => void
  onRecordingComplete?: (audioBlob: Blob) => void
  maxDuration?: number // in seconds
  realTimeTranscription?: boolean
  className?: string
}

export function VoiceRecorder({
  onTranscript,
  onRecordingComplete,
  maxDuration = 120, // 2 minutes default
  realTimeTranscription = true,
  className
}: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [_isPaused, _setIsPaused] = useState(false)
  const [duration, setDuration] = useState(0)
  const [transcript, setTranscript] = useState('')
  const [audioLevel, setAudioLevel] = useState(0)
  const [error, setError] = useState<string | null>(null)
  
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationRef = useRef<number | null>(null)

  useEffect(() => {
    // Check for browser support
    if (!voiceService.isSupported()) {
      setError('Voice recording is not supported in your browser')
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
      if (audioContextRef.current) audioContextRef.current.close()
    }
  }, [])

  const startRecording = async () => {
    try {
      setError(null)
      
      // Start audio recording
      await voiceService.startRecording()
      
      // Set up audio visualization
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      audioContextRef.current = new AudioContext()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 256
      source.connect(analyserRef.current)
      
      // Start real-time transcription if enabled
      if (realTimeTranscription && voiceService.isSpeechRecognitionSupported()) {
        voiceService.startSpeechRecognition(
          (text, isFinal) => {
            setTranscript(text)
            if (isFinal) {
              onTranscript(text)
            }
          },
          (error) => {
            console.error('Speech recognition error:', error)
            // Continue recording even if speech recognition fails
          }
        )
      }
      
      setIsRecording(true)
      setDuration(0)
      
      // Start duration timer
      timerRef.current = setInterval(() => {
        setDuration(prev => {
          const newDuration = prev + 1
          if (newDuration >= maxDuration) {
            stopRecording()
            toast.error(`Maximum recording duration (${maxDuration}s) reached`)
          }
          return newDuration
        })
      }, 1000)
      
      // Start audio level animation
      updateAudioLevel()
    } catch (error) {
      setError('Failed to start recording. Please check microphone permissions.')
      console.error(error)
    }
  }

  const updateAudioLevel = () => {
    if (!analyserRef.current || !isRecording) return
    
    const level = voiceService.getAudioLevel(analyserRef.current)
    setAudioLevel(level)
    
    animationRef.current = requestAnimationFrame(updateAudioLevel)
  }

  const stopRecording = async () => {
    try {
      // Stop timers and animations
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }
      
      // Stop speech recognition
      if (realTimeTranscription) {
        voiceService.stopSpeechRecognition()
      }
      
      // Stop recording and get audio blob
      const audioBlob = await voiceService.stopRecording()
      
      // Close audio context
      if (audioContextRef.current) {
        audioContextRef.current.close()
        audioContextRef.current = null
      }
      
      setIsRecording(false)
      setAudioLevel(0)
      
      // If no real-time transcription, transcribe the full audio
      if (!realTimeTranscription || !transcript) {
        toast.loading('Transcribing audio...')
        try {
          const result = await voiceService.transcribeAudio(audioBlob)
          setTranscript(result.text)
          onTranscript(result.text)
          toast.dismiss()
          toast.success('Transcription complete')
        } catch (error) {
          toast.dismiss()
          toast.error('Failed to transcribe audio')
          console.error(error)
        }
      }
      
      onRecordingComplete?.(audioBlob)
    } catch (error) {
      setError('Failed to stop recording')
      console.error(error)
    }
  }

  const cancelRecording = () => {
    voiceService.cancelRecording()
    voiceService.stopSpeechRecognition()
    
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    
    setIsRecording(false)
    setDuration(0)
    setTranscript('')
    setAudioLevel(0)
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (error && !voiceService.isSupported()) {
    return (
      <div className={cn("text-center p-4", className)}>
        <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-sm text-red-600">{error}</p>
      </div>
    )
  }

  return (
    <div className={cn("relative", className)}>
      {!isRecording ? (
        <Button
          onClick={startRecording}
          variant="outline"
          size="icon"
          className="relative"
          title="Start voice recording"
        >
          <Mic className="w-5 h-5" />
        </Button>
      ) : (
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-2 shadow-lg"
          >
            {/* Recording indicator */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                {audioLevel > 0 && (
                  <div 
                    className="absolute inset-0 bg-red-400 rounded-full animate-ping"
                    style={{ 
                      transform: `scale(${1 + audioLevel * 2})`,
                      opacity: audioLevel * 0.5 
                    }}
                  />
                )}
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {formatDuration(duration)}
              </span>
            </div>

            {/* Audio level indicator */}
            <div className="flex items-center gap-1">
              <Volume2 className="w-4 h-4 text-gray-500" />
              <div className="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-purple-500"
                  animate={{ width: `${audioLevel * 100}%` }}
                  transition={{ duration: 0.1 }}
                />
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-1 ml-2">
              <Button
                size="icon"
                variant="ghost"
                onClick={cancelRecording}
                className="h-8 w-8"
                title="Cancel recording"
              >
                <X className="w-4 h-4" />
              </Button>
              
              <Button
                size="icon"
                onClick={stopRecording}
                className="h-8 w-8 bg-red-500 hover:bg-red-600"
                title="Stop recording"
              >
                <Square className="w-4 h-4 text-white" />
              </Button>
            </div>
          </motion.div>
        </AnimatePresence>
      )}

      {/* Real-time transcript preview */}
      {isRecording && realTimeTranscription && transcript && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute bottom-full mb-2 left-0 right-0 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 shadow-lg max-w-sm"
        >
          <p className="text-sm text-gray-700 dark:text-gray-300 italic">
            "{transcript}"
          </p>
        </motion.div>
      )}
    </div>
  )
}