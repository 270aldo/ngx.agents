'use client'

import { useState, useRef, KeyboardEvent } from 'react'
import { Send, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { AttachmentPreview } from './AttachmentPreview'
import { VoiceRecorder } from './VoiceRecorder'
import { cn } from '@/utils/cn'
import uploadService, { UploadResponse } from '@/services/upload'
import { toast } from 'react-hot-toast'

interface Attachment extends File {
  uploadId?: string
  uploadResponse?: UploadResponse
  uploading?: boolean
  progress?: number
  error?: string
}

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (value: string, attachments?: UploadResponse[]) => void
  onTyping?: (isTyping: boolean) => void
  disabled?: boolean
  placeholder?: string
  maxFileSize?: number // in MB
  allowedFileTypes?: string[]
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  onTyping,
  disabled,
  placeholder = 'Type your message...',
  maxFileSize = 10, // 10MB default
  allowedFileTypes = ['image/*', '.pdf', '.doc', '.docx', '.txt']
}: ChatInputProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)

  const handleSubmit = async () => {
    if (value.trim() || attachments.length > 0) {
      // Wait for all uploads to complete
      const uploadedAttachments = attachments
        .filter(a => a.uploadResponse && !a.error)
        .map(a => a.uploadResponse!)
      
      if (attachments.some(a => a.uploading)) {
        toast.error('Please wait for uploads to complete')
        return
      }
      
      if (attachments.some(a => a.error)) {
        toast.error('Some files failed to upload')
        return
      }
      
      onSubmit(value, uploadedAttachments)
      setAttachments([])
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    
    // Validate and upload files
    for (const file of files) {
      // Validate file
      const validation = uploadService.validateFile(file, {
        maxSize: maxFileSize * 1024 * 1024,
        allowedTypes: allowedFileTypes.filter(t => !t.startsWith('.')),
        allowedExtensions: allowedFileTypes.filter(t => t.startsWith('.')).map(t => t.slice(1))
      })
      
      if (!validation.valid) {
        toast.error(validation.error || 'Invalid file')
        continue
      }
      
      // Create attachment object
      const attachment: Attachment = Object.assign(file, {
        uploadId: Math.random().toString(36).substring(7),
        uploading: true,
        progress: 0
      })
      
      // Add to state
      setAttachments(prev => [...prev, attachment])
      
      // Start upload
      try {
        const response = await uploadService.uploadFile(
          file,
          (progress) => {
            setAttachments(prev => prev.map(a => 
              a.uploadId === attachment.uploadId 
                ? { ...a, progress } 
                : a
            ))
          }
        )
        
        // Update with response
        setAttachments(prev => prev.map(a => 
          a.uploadId === attachment.uploadId 
            ? { ...a, uploadResponse: response, uploading: false, progress: 100 } 
            : a
        ))
        
        toast.success(`${file.name} uploaded successfully`)
      } catch (_error) {
        // Update with error
        setAttachments(prev => prev.map(a => 
          a.uploadId === attachment.uploadId 
            ? { ...a, error: 'Upload failed', uploading: false } 
            : a
        ))
        
        toast.error(`Failed to upload ${file.name}`)
      }
    }
    
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeAttachment = async (index: number) => {
    const attachment = attachments[index]
    
    // Delete from server if uploaded
    if (attachment.uploadResponse?.id) {
      try {
        await uploadService.deleteFile(attachment.uploadResponse.id)
      } catch (error) {
        console.error('Failed to delete file:', error)
      }
    }
    
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }

  const handleVoiceTranscript = (transcript: string) => {
    // Append transcript to current input
    onChange(value + (value ? ' ' : '') + transcript)
    adjustTextareaHeight()
  }

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    // Only set dragging to false if we're leaving the drop zone entirely
    if (dropZoneRef.current && !dropZoneRef.current.contains(e.relatedTarget as Node)) {
      setIsDragging(false)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      // Simulate file input change event
      const fakeEvent = {
        target: { files: e.dataTransfer.files }
      } as unknown as React.ChangeEvent<HTMLInputElement>
      
      await handleFileSelect(fakeEvent)
    }
  }

  return (
    <div 
      className="space-y-2 relative"
      ref={dropZoneRef}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="absolute inset-0 bg-purple-500 bg-opacity-10 border-2 border-dashed border-purple-500 rounded-lg z-10 flex items-center justify-center">
          <div className="text-center">
            <Paperclip className="w-12 h-12 text-purple-600 mx-auto mb-2" />
            <p className="text-purple-600 font-medium">Drop files here to upload</p>
            <p className="text-sm text-purple-500">
              Max {maxFileSize}MB per file
            </p>
          </div>
        </div>
      )}

      {/* Attachments preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-3 px-4">
          {attachments.map((attachment, index) => (
            <AttachmentPreview
              key={attachment.uploadId || index}
              file={attachment}
              onRemove={() => removeAttachment(index)}
              uploading={attachment.uploading}
              uploadProgress={attachment.progress}
              error={attachment.error}
            />
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-2 px-4 pb-4">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          accept={allowedFileTypes.join(',')}
        />
        
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="mb-1"
        >
          <Paperclip className="h-5 w-5" />
        </Button>

        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              onChange(e.target.value)
              adjustTextareaHeight()
              onTyping?.(true)
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={cn(
              'w-full resize-none rounded-lg border bg-background px-4 py-3 pr-12',
              'text-sm ring-offset-background transition-all duration-200',
              'placeholder:text-muted-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              'disabled:cursor-not-allowed disabled:opacity-50',
              'min-h-[48px] max-h-[120px]',
              disabled && 'bg-gray-50 dark:bg-gray-900'
            )}
          />
          
          <div className="absolute bottom-2 right-2 flex gap-1">
            <VoiceRecorder
              onTranscript={handleVoiceTranscript}
              realTimeTranscription={true}
              maxDuration={120}
            />
            
            <Button
              type="button"
              size="icon"
              onClick={handleSubmit}
              disabled={disabled || (!value.trim() && attachments.length === 0)}
              className="h-8 w-8"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}