'use client'

import { useState, useEffect } from 'react'
import { Volume2, VolumeX, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import voiceService from '@/services/voice'
import { cn } from '@/utils/cn'

interface VoiceFeedbackProps {
  text: string
  autoPlay?: boolean
  voice?: string
  speed?: number
  onStart?: () => void
  onEnd?: () => void
  className?: string
}

export function VoiceFeedback({
  text,
  autoPlay = false,
  voice,
  speed = 1,
  onStart,
  onEnd,
  className
}: VoiceFeedbackProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isMuted, setIsMuted] = useState(false)

  useEffect(() => {
    // Load available voices
    const loadVoices = () => {
      const voices = voiceService.getAvailableVoices()
      console.log('Available voices:', voices)
    }

    if ('speechSynthesis' in window) {
      speechSynthesis.addEventListener('voiceschanged', loadVoices)
      loadVoices()
    }

    return () => {
      if ('speechSynthesis' in window) {
        speechSynthesis.removeEventListener('voiceschanged', loadVoices)
        speechSynthesis.cancel()
      }
    }
  }, [])

  useEffect(() => {
    if (autoPlay && text && !isMuted) {
      playAudio()
    }
  }, [text, autoPlay])

  const playAudio = async () => {
    if (isPlaying || !text) return

    setIsLoading(true)
    setIsPlaying(true)
    onStart?.()

    try {
      await voiceService.textToSpeech(text, { voice, speed })
      onEnd?.()
    } catch (error) {
      console.error('TTS error:', error)
    } finally {
      setIsLoading(false)
      setIsPlaying(false)
    }
  }

  const stopAudio = () => {
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel()
    }
    setIsPlaying(false)
  }

  const toggleMute = () => {
    setIsMuted(!isMuted)
    if (isPlaying) {
      stopAudio()
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={isMuted ? toggleMute : isPlaying ? stopAudio : playAudio}
      disabled={isLoading || !text}
      className={cn("relative", className)}
      title={isMuted ? "Unmute" : isPlaying ? "Stop" : "Play audio"}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : isMuted ? (
        <VolumeX className="w-4 h-4" />
      ) : (
        <Volume2 className={cn("w-4 h-4", isPlaying && "text-purple-600")} />
      )}
      
      {isPlaying && !isLoading && (
        <span className="absolute -top-1 -right-1 flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
        </span>
      )}
    </Button>
  )
}