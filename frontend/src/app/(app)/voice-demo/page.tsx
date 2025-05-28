'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { VoiceRecorder } from '@/components/chat/VoiceRecorder'
import { VoiceCommands } from '@/components/chat/VoiceCommands'
import { VoiceFeedback } from '@/components/chat/VoiceFeedback'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { 
  Mic, 
  Volume2, 
  Command,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  Info
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import voiceService from '@/services/voice'

export default function VoiceDemoPage() {
  const [transcript, setTranscript] = useState('')
  const [ttsText, setTtsText] = useState('')
  const [lastCommand, setLastCommand] = useState<{ command: string; action: string; params?: unknown; timestamp: Date } | null>(null)

  const sampleTexts = [
    "Hola, soy tu asistente de fitness. ¿En qué puedo ayudarte hoy?",
    "Tu progreso esta semana ha sido excelente. Has completado 5 entrenamientos.",
    "Recuerda hidratarte bien durante tu entrenamiento.",
    "Tu próxima sesión está programada para mañana a las 8 AM."
  ]

  const handleVoiceCommand = (command: string, action: string, params?: unknown) => {
    setLastCommand({ command, action, params, timestamp: new Date() })
    toast.success(`Command received: ${action}`)
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-navy-700">
            Voice Interaction Demo
          </CardTitle>
          <p className="text-gray-600 mt-2">
            Test voice recording, speech-to-text, text-to-speech, and voice commands
          </p>
        </CardHeader>
      </Card>

      {/* Feature Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Feature Support</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4" />
                <span className="text-sm">Voice Recording</span>
              </div>
              <Badge variant={voiceService.isSupported() ? "success" : "destructive"}>
                {voiceService.isSupported() ? "Supported" : "Not Supported"}
              </Badge>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                <span className="text-sm">Speech Recognition</span>
              </div>
              <Badge variant={voiceService.isSpeechRecognitionSupported() ? "success" : "destructive"}>
                {voiceService.isSpeechRecognitionSupported() ? "Supported" : "Not Supported"}
              </Badge>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4" />
                <span className="text-sm">Text-to-Speech</span>
              </div>
              <Badge variant={'speechSynthesis' in window ? "success" : "destructive"}>
                {'speechSynthesis' in window ? "Supported" : "Not Supported"}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Voice Recording */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Mic className="w-5 h-5 text-purple-600" />
            Voice Recording & Transcription
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <VoiceRecorder
              onTranscript={(text) => {
                setTranscript(text)
                toast.success('Transcription completed')
              }}
              realTimeTranscription={true}
              maxDuration={60}
            />
            <p className="text-sm text-gray-600">
              Click the microphone to start recording. Real-time transcription enabled.
            </p>
          </div>
          
          {transcript && (
            <div className="p-4 bg-purple-50 rounded-lg">
              <p className="text-sm font-medium text-purple-900 mb-1">Transcript:</p>
              <p className="text-purple-700">{transcript}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Text-to-Speech */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-purple-600" />
            Text-to-Speech
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Click the speaker icon next to any text to hear it spoken aloud.
            </p>
            
            {sampleTexts.map((text, index) => (
              <div 
                key={index}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
              >
                <VoiceFeedback 
                  text={text}
                  autoPlay={false}
                />
                <p className="text-sm flex-1">{text}</p>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            <textarea
              value={ttsText}
              onChange={(e) => setTtsText(e.target.value)}
              placeholder="Enter custom text to speak..."
              className="w-full p-3 border border-gray-300 rounded-lg resize-none"
              rows={3}
            />
            <div className="flex gap-2">
              <VoiceFeedback 
                text={ttsText}
                autoPlay={false}
              />
              <Button
                variant="outline"
                onClick={() => setTtsText('')}
                disabled={!ttsText}
              >
                Clear
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Voice Commands */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Command className="w-5 h-5 text-purple-600" />
            Voice Commands
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <VoiceCommands
              enabled={true}
              onCommand={handleVoiceCommand}
            />
            <div className="flex-1">
              <p className="text-sm text-gray-600">
                Click the microphone or press <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">Ctrl+Shift+M</kbd> to activate voice commands.
              </p>
            </div>
          </div>

          <div className="p-4 bg-blue-50 rounded-lg">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-blue-600 mt-0.5" />
              <div className="text-sm text-blue-800">
                <p className="font-medium mb-1">Available commands:</p>
                <ul className="list-disc list-inside space-y-1 text-blue-700">
                  <li>&quot;Muestra mi progreso&quot; - Navigate to progress page</li>
                  <li>&quot;Abre dashboard&quot; - Navigate to dashboard</li>
                  <li>&quot;Busca agentes&quot; - Navigate to agents</li>
                  <li>&quot;Registra mi peso&quot; - Open weight log</li>
                  <li>&quot;Analiza mi entrenamiento&quot; - Analyze workout</li>
                  <li>&quot;Ayuda&quot; - Show help</li>
                </ul>
              </div>
            </div>
          </div>

          {lastCommand && (
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-sm font-medium text-green-900 mb-2">Last Command:</p>
              <div className="space-y-1 text-sm text-green-700">
                <p><strong>Text:</strong> {lastCommand.command}</p>
                <p><strong>Action:</strong> {lastCommand.action}</p>
                {lastCommand.params && (
                  <p><strong>Parameters:</strong> {JSON.stringify(lastCommand.params)}</p>
                )}
                <p className="text-xs text-green-600">
                  {lastCommand.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Instructions */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-3">
            <div className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
              <p className="text-sm">
                <strong>Privacy:</strong> Voice processing happens locally in your browser when possible. 
                Only transcription requests are sent to the server.
              </p>
            </div>
            
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
              <p className="text-sm">
                <strong>Browser Support:</strong> Voice features work best in Chrome, Edge, and Safari. 
                Firefox has limited support.
              </p>
            </div>
            
            <div className="flex items-start gap-2">
              <Info className="w-5 h-5 text-blue-500 mt-0.5" />
              <p className="text-sm">
                <strong>Permissions:</strong> You&apos;ll need to grant microphone access for voice features to work.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}