import { api } from '@/lib/api'

export interface TranscriptionResult {
  text: string
  confidence: number
  language?: string
  duration?: number
}

export interface VoiceCommand {
  command: string
  action: string
  parameters?: Record<string, unknown>
}

class VoiceService {
  private mediaRecorder: MediaRecorder | null = null
  private audioChunks: Blob[] = []
  private recognition: SpeechRecognition | null = null
  private isListening = false

  constructor() {
    // Initialize Web Speech API if available
    if (typeof window !== 'undefined' && 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = (window as typeof window & { webkitSpeechRecognition: typeof SpeechRecognition }).webkitSpeechRecognition
      this.recognition = new SpeechRecognition()
      this.recognition.continuous = true
      this.recognition.interimResults = true
      this.recognition.lang = 'es-ES' // Spanish by default, can be changed
    }
  }

  /**
   * Check if voice recording is supported
   */
  isSupported(): boolean {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
  }

  /**
   * Check if speech recognition is supported
   */
  isSpeechRecognitionSupported(): boolean {
    return !!this.recognition
  }

  /**
   * Start recording audio
   */
  async startRecording(onDataAvailable?: (blob: Blob) => void): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Create MediaRecorder with the stream
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      this.audioChunks = []
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
          onDataAvailable?.(event.data)
        }
      }
      
      this.mediaRecorder.start(1000) // Collect data every second
    } catch (error) {
      console.error('Error starting recording:', error)
      throw new Error('Failed to start recording. Please check microphone permissions.')
    }
  }

  /**
   * Stop recording and return the audio blob
   */
  async stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        reject(new Error('No recording in progress'))
        return
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' })
        this.audioChunks = []
        
        // Stop all tracks to release the microphone
        this.mediaRecorder?.stream.getTracks().forEach(track => track.stop())
        this.mediaRecorder = null
        
        resolve(audioBlob)
      }

      this.mediaRecorder.stop()
    })
  }

  /**
   * Cancel recording without saving
   */
  cancelRecording(): void {
    if (this.mediaRecorder) {
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop())
      this.mediaRecorder = null
      this.audioChunks = []
    }
  }

  /**
   * Check if currently recording
   */
  isRecording(): boolean {
    return this.mediaRecorder?.state === 'recording'
  }

  /**
   * Start speech recognition (real-time transcription)
   */
  startSpeechRecognition(
    onResult: (transcript: string, isFinal: boolean) => void,
    onError?: (error: Error) => void
  ): void {
    if (!this.recognition) {
      onError?.(new Error('Speech recognition not supported'))
      return
    }

    this.recognition.onresult = (event: SpeechRecognitionEvent) => {
      const results = event.results
      const lastResult = results[results.length - 1]
      const transcript = lastResult[0].transcript
      const isFinal = lastResult.isFinal

      onResult(transcript, isFinal)
    }

    this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      onError?.(new Error(`Speech recognition error: ${event.error}`))
    }

    this.recognition.onend = () => {
      this.isListening = false
    }

    this.recognition.start()
    this.isListening = true
  }

  /**
   * Stop speech recognition
   */
  stopSpeechRecognition(): void {
    if (this.recognition && this.isListening) {
      this.recognition.stop()
      this.isListening = false
    }
  }

  /**
   * Transcribe audio file using backend API
   */
  async transcribeAudio(audioBlob: Blob): Promise<TranscriptionResult> {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')

    const response = await api.post<TranscriptionResult>('/voice/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    return response.data
  }

  /**
   * Convert text to speech
   */
  async textToSpeech(text: string, options?: {
    voice?: string
    speed?: number
    pitch?: number
  }): Promise<void> {
    // Use Web Speech API for TTS
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text)
      
      if (options?.voice) {
        const voices = speechSynthesis.getVoices()
        const selectedVoice = voices.find(v => v.name === options.voice)
        if (selectedVoice) utterance.voice = selectedVoice
      }
      
      utterance.rate = options?.speed || 1
      utterance.pitch = options?.pitch || 1
      utterance.lang = 'es-ES'
      
      return new Promise((resolve, reject) => {
        utterance.onend = () => resolve()
        utterance.onerror = (error) => reject(error)
        speechSynthesis.speak(utterance)
      })
    } else {
      // Fallback to backend TTS
      const response = await api.post('/voice/tts', {
        text,
        ...options
      }, {
        responseType: 'blob'
      })

      const audio = new Audio(URL.createObjectURL(response.data))
      return audio.play()
    }
  }

  /**
   * Get available voices for TTS
   */
  getAvailableVoices(): SpeechSynthesisVoice[] {
    if ('speechSynthesis' in window) {
      return speechSynthesis.getVoices()
    }
    return []
  }

  /**
   * Parse voice commands from text
   */
  parseVoiceCommand(text: string): VoiceCommand | null {
    const commands = [
      { pattern: /^(muestra|mostrar?)\s+(.+)$/i, action: 'show' },
      { pattern: /^(busca|buscar)\s+(.+)$/i, action: 'search' },
      { pattern: /^(abre|abrir)\s+(.+)$/i, action: 'open' },
      { pattern: /^(crea|crear)\s+(.+)$/i, action: 'create' },
      { pattern: /^(registra|registrar)\s+(.+)$/i, action: 'log' },
      { pattern: /^(analiza|analizar)\s+(.+)$/i, action: 'analyze' },
      { pattern: /^ayuda$/i, action: 'help' },
      { pattern: /^(cancela|cancelar)$/i, action: 'cancel' },
    ]

    for (const { pattern, action } of commands) {
      const match = text.match(pattern)
      if (match) {
        return {
          command: text,
          action,
          parameters: match[2] ? { query: match[2] } : undefined
        }
      }
    }

    return null
  }

  /**
   * Create audio visualization
   */
  createAudioVisualizer(
    audioContext: AudioContext,
    source: MediaStreamAudioSourceNode,
    canvas: HTMLCanvasElement
  ): () => void {
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)

    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    const ctx = canvas.getContext('2d')!
    
    let animationId: number

    const draw = () => {
      animationId = requestAnimationFrame(draw)
      
      analyser.getByteFrequencyData(dataArray)
      
      ctx.fillStyle = 'rgb(20, 20, 20)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      
      const barWidth = (canvas.width / bufferLength) * 2.5
      let barHeight: number
      let x = 0
      
      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * canvas.height
        
        const r = barHeight + 25 * (i / bufferLength)
        const g = 250 * (i / bufferLength)
        const b = 50
        
        ctx.fillStyle = `rgb(${r},${g},${b})`
        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight)
        
        x += barWidth + 1
      }
    }

    draw()

    // Return cleanup function
    return () => {
      cancelAnimationFrame(animationId)
      analyser.disconnect()
    }
  }

  /**
   * Get audio level (for volume indicator)
   */
  getAudioLevel(analyser: AnalyserNode): number {
    const dataArray = new Uint8Array(analyser.frequencyBinCount)
    analyser.getByteFrequencyData(dataArray)
    
    const average = dataArray.reduce((a, b) => a + b) / dataArray.length
    return average / 255 // Normalize to 0-1
  }
}

const voiceService = new VoiceService()
export default voiceService