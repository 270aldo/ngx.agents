'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { ChatInput } from '@/components/chat/ChatInput'
import { UploadResponse } from '@/services/upload'
import { toast } from 'react-hot-toast'
import { FileText, Image, File, Video, Music, CheckCircle } from 'lucide-react'

export default function UploadDemoPage() {
  const [message, setMessage] = useState('')
  const [uploadedFiles, setUploadedFiles] = useState<UploadResponse[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (content: string, attachments?: UploadResponse[]) => {
    setIsSubmitting(true)
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      if (attachments?.length) {
        setUploadedFiles(prev => [...prev, ...attachments])
        toast.success(`Message sent with ${attachments.length} attachment(s)`)
      } else {
        toast.success('Message sent successfully')
      }
      
      setMessage('')
    } catch (_error) {
      toast.error('Failed to send message')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <Image className="w-5 h-5" alt="" />
    if (type.startsWith('video/')) return <Video className="w-5 h-5" />
    if (type.startsWith('audio/')) return <Music className="w-5 h-5" />
    if (type.includes('pdf') || type.includes('document')) return <FileText className="w-5 h-5" />
    return <File className="w-5 h-5" />
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-navy-700">
            Multimodal Upload Demo
          </CardTitle>
          <p className="text-gray-600 mt-2">
            Test the enhanced file upload functionality with drag & drop, progress tracking, and preview
          </p>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Features List */}
          <div className="bg-purple-50 rounded-lg p-4 space-y-2">
            <h3 className="font-semibold text-purple-900 mb-2">Features:</h3>
            <ul className="space-y-1 text-sm text-purple-700">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Drag & drop files directly onto the chat input
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Real-time upload progress tracking
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Image preview with full-screen view
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                File validation (size, type)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Multiple file selection
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                Automatic file upload on selection
              </li>
            </ul>
          </div>

          {/* Upload History */}
          {uploadedFiles.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Upload History:</h3>
              <div className="space-y-2">
                {uploadedFiles.map((file, index) => (
                  <div 
                    key={index}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="p-2 bg-white rounded-lg border border-gray-200">
                      {getFileIcon(file.type)}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-sm">{file.name}</p>
                      <p className="text-xs text-gray-500">
                        {file.type} • {(file.size / 1024).toFixed(1)}KB
                      </p>
                    </div>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Instructions */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-2">Try it out:</h3>
            <ol className="space-y-2 text-sm text-gray-700 list-decimal list-inside">
              <li>Click the paperclip icon to select files</li>
              <li>Or drag and drop files directly onto the input area</li>
              <li>Watch the upload progress</li>
              <li>Click on images to preview them in full screen</li>
              <li>Type a message and send with attachments</li>
            </ol>
          </div>

          {/* File Type Support */}
          <div className="text-sm text-gray-600">
            <p className="font-medium mb-1">Supported file types:</p>
            <p>Images (PNG, JPG, GIF, WebP), Documents (PDF, DOC, DOCX), Text files</p>
            <p className="mt-1">Maximum file size: 10MB per file</p>
          </div>
        </CardContent>
      </Card>

      {/* Chat Input */}
      <Card className="mt-6 sticky bottom-4">
        <CardContent className="p-0">
          <ChatInput
            value={message}
            onChange={setMessage}
            onSubmit={handleSubmit}
            disabled={isSubmitting}
            placeholder="Type a message or drop files here..."
            maxFileSize={10}
            allowedFileTypes={[
              'image/*',
              '.pdf',
              '.doc',
              '.docx',
              '.txt',
              '.csv',
              '.xls',
              '.xlsx'
            ]}
          />
        </CardContent>
      </Card>
    </div>
  )
}