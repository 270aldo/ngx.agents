import { api } from '@/lib/api'

export interface UploadResponse {
  id: string
  url: string
  thumbnail_url?: string
  type: string
  size: number
  name: string
  metadata?: {
    width?: number
    height?: number
    duration?: number
    pages?: number
  }
}

export interface ProcessedDocument {
  id: string
  content: string
  summary?: string
  metadata?: Record<string, unknown>
}

class UploadService {
  /**
   * Upload a single file
   */
  async uploadFile(file: File, onProgress?: (progress: number) => void): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<UploadResponse>('/upload/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress?.(progress)
        }
      }
    })

    return response.data
  }

  /**
   * Upload multiple files
   */
  async uploadFiles(files: File[], onProgress?: (progress: number) => void): Promise<UploadResponse[]> {
    const formData = new FormData()
    files.forEach((file, _index) => {
      formData.append(`files`, file)
    })

    const response = await api.post<UploadResponse[]>('/upload/files', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress?.(progress)
        }
      }
    })

    return response.data
  }

  /**
   * Upload and process an image
   */
  async uploadImage(file: File, options?: {
    resize?: { width: number; height: number }
    quality?: number
    format?: 'webp' | 'jpeg' | 'png'
  }): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    
    if (options) {
      formData.append('options', JSON.stringify(options))
    }

    const response = await api.post<UploadResponse>('/upload/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    return response.data
  }

  /**
   * Upload and process a document (PDF, DOC, etc)
   */
  async uploadDocument(file: File): Promise<ProcessedDocument> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<ProcessedDocument>('/upload/document', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    return response.data
  }

  /**
   * Delete an uploaded file
   */
  async deleteFile(fileId: string): Promise<void> {
    await api.delete(`/upload/file/${fileId}`)
  }

  /**
   * Get file preview URL
   */
  getPreviewUrl(fileId: string, options?: {
    width?: number
    height?: number
    quality?: number
  }): string {
    const params = new URLSearchParams()
    if (options?.width) params.append('w', options.width.toString())
    if (options?.height) params.append('h', options.height.toString())
    if (options?.quality) params.append('q', options.quality.toString())

    const queryString = params.toString()
    return `${api.defaults.baseURL}/upload/preview/${fileId}${queryString ? `?${queryString}` : ''}`
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File, options?: {
    maxSize?: number // in bytes
    allowedTypes?: string[]
    allowedExtensions?: string[]
  }): { valid: boolean; error?: string } {
    const { maxSize = 10 * 1024 * 1024, allowedTypes, allowedExtensions } = options || {}

    // Check file size
    if (file.size > maxSize) {
      return { 
        valid: false, 
        error: `File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit` 
      }
    }

    // Check file type
    if (allowedTypes && !allowedTypes.some(type => file.type.startsWith(type))) {
      return { 
        valid: false, 
        error: `File type ${file.type} is not allowed` 
      }
    }

    // Check file extension
    if (allowedExtensions) {
      const extension = file.name.split('.').pop()?.toLowerCase()
      if (!extension || !allowedExtensions.includes(extension)) {
        return { 
          valid: false, 
          error: `File extension .${extension} is not allowed` 
        }
      }
    }

    return { valid: true }
  }

  /**
   * Get file type category
   */
  getFileCategory(file: File): 'image' | 'document' | 'video' | 'audio' | 'other' {
    if (file.type.startsWith('image/')) return 'image'
    if (file.type.startsWith('video/')) return 'video'
    if (file.type.startsWith('audio/')) return 'audio'
    if (
      file.type.includes('pdf') ||
      file.type.includes('document') ||
      file.type.includes('text') ||
      file.type.includes('sheet') ||
      file.type.includes('presentation')
    ) {
      return 'document'
    }
    return 'other'
  }

  /**
   * Generate thumbnail for image
   */
  async generateThumbnail(file: File, maxSize: number = 200): Promise<Blob> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      
      reader.onload = (e) => {
        const img = new Image()
        
        img.onload = () => {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')
          if (!ctx) {
            reject(new Error('Could not get canvas context'))
            return
          }

          // Calculate new dimensions
          let width = img.width
          let height = img.height
          
          if (width > height) {
            if (width > maxSize) {
              height = height * (maxSize / width)
              width = maxSize
            }
          } else {
            if (height > maxSize) {
              width = width * (maxSize / height)
              height = maxSize
            }
          }

          canvas.width = width
          canvas.height = height

          // Draw the image
          ctx.drawImage(img, 0, 0, width, height)

          // Convert to blob
          canvas.toBlob((blob) => {
            if (blob) {
              resolve(blob)
            } else {
              reject(new Error('Could not generate thumbnail'))
            }
          }, 'image/jpeg', 0.8)
        }

        img.onerror = () => reject(new Error('Could not load image'))
        img.src = e.target?.result as string
      }

      reader.onerror = () => reject(new Error('Could not read file'))
      reader.readAsDataURL(file)
    })
  }
}

const uploadService = new UploadService()
export default uploadService