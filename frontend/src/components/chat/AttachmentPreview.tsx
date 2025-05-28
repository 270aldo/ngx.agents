'use client'

import { useState, useEffect } from 'react'
import { 
  FileText, 
  File, 
  Music, 
  Video, 
  X, 
  Eye, 
  Download,
  Loader2,
  AlertCircle
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { motion, AnimatePresence } from 'framer-motion'
import uploadService from '@/services/upload'

interface AttachmentPreviewProps {
  file: File
  onRemove: () => void
  uploading?: boolean
  uploadProgress?: number
  error?: string
  className?: string
}

export function AttachmentPreview({
  file,
  onRemove,
  uploading = false,
  uploadProgress = 0,
  error,
  className
}: AttachmentPreviewProps) {
  const [preview, setPreview] = useState<string | null>(null)
  const [showFullPreview, setShowFullPreview] = useState(false)

  useEffect(() => {
    // Generate preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => setPreview(e.target?.result as string)
      reader.readAsDataURL(file)
    }

    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file])

  const getFileIcon = () => {
    const category = uploadService.getFileCategory(file)
    switch (category) {
      case 'image':
        return null // Show preview instead
      case 'document':
        return <FileText className="w-8 h-8 text-blue-500" />
      case 'video':
        return <Video className="w-8 h-8 text-purple-500" />
      case 'audio':
        return <Music className="w-8 h-8 text-green-500" />
      default:
        return <File className="w-8 h-8 text-gray-500" />
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        className={cn(
          "relative group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700",
          "overflow-hidden transition-all hover:shadow-md",
          error && "border-red-500",
          className
        )}
      >
        {/* Preview Area */}
        <div className="relative h-24 w-24 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
          {preview ? (
            <img
              src={preview}
              alt={file.name}
              className="h-full w-full object-cover"
            />
          ) : (
            getFileIcon()
          )}

          {/* Upload Progress Overlay */}
          {uploading && (
            <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-6 h-6 text-white animate-spin mx-auto mb-1" />
                <span className="text-xs text-white font-medium">
                  {uploadProgress}%
                </span>
              </div>
            </div>
          )}

          {/* Error Overlay */}
          {error && (
            <div className="absolute inset-0 bg-red-500 bg-opacity-90 flex items-center justify-center p-2">
              <div className="text-center">
                <AlertCircle className="w-6 h-6 text-white mx-auto mb-1" />
                <span className="text-xs text-white">Error</span>
              </div>
            </div>
          )}

          {/* Hover Actions */}
          {!uploading && !error && (
            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
              {preview && (
                <button
                  onClick={() => setShowFullPreview(true)}
                  className="p-1.5 bg-white rounded-full mr-1"
                  title="Preview"
                >
                  <Eye className="w-4 h-4 text-gray-700" />
                </button>
              )}
              <button
                onClick={onRemove}
                className="p-1.5 bg-white rounded-full"
                title="Remove"
              >
                <X className="w-4 h-4 text-gray-700" />
              </button>
            </div>
          )}
        </div>

        {/* File Info */}
        <div className="p-2">
          <p className="text-xs font-medium text-gray-900 dark:text-gray-100 truncate" title={file.name}>
            {file.name}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {formatFileSize(file.size)}
          </p>
          {error && (
            <p className="text-xs text-red-500 mt-1 truncate" title={error}>
              {error}
            </p>
          )}
        </div>

        {/* Progress Bar */}
        {uploading && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200 dark:bg-gray-700">
            <motion.div
              className="h-full bg-purple-500"
              initial={{ width: 0 }}
              animate={{ width: `${uploadProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        )}
      </motion.div>

      {/* Full Preview Modal */}
      <AnimatePresence>
        {showFullPreview && preview && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
            onClick={() => setShowFullPreview(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="relative max-w-4xl max-h-[90vh] overflow-hidden rounded-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <img
                src={preview}
                alt={file.name}
                className="max-w-full max-h-full object-contain"
              />
              
              <div className="absolute top-4 right-4 flex gap-2">
                <button
                  onClick={() => {
                    const a = document.createElement('a')
                    a.href = preview
                    a.download = file.name
                    a.click()
                  }}
                  className="p-2 bg-white dark:bg-gray-800 rounded-full shadow-lg hover:shadow-xl transition-shadow"
                  title="Download"
                >
                  <Download className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setShowFullPreview(false)}
                  className="p-2 bg-white dark:bg-gray-800 rounded-full shadow-lg hover:shadow-xl transition-shadow"
                  title="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 rounded-lg p-3 shadow-lg">
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}