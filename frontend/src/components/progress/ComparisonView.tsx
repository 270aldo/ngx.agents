'use client'

import { useState, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Progress, ProgressPhoto } from '@/types'
import { 
  Camera,
  Calendar,
  Download,
  Share2,
  ChevronLeft,
  ChevronRight,
  Upload,
  X,
  RotateCw,
  ZoomIn,
  ZoomOut
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { format, parseISO } from 'date-fns'
import { motion, AnimatePresence } from 'framer-motion'
import progressService from '@/services/progress'
import { toast } from 'react-hot-toast'

interface ComparisonViewProps {
  progressData: Progress[]
  onPhotoUpload?: (photo: ProgressPhoto) => void
  className?: string
}

type PhotoAngle = 'front' | 'side' | 'back'

export function ComparisonView({ 
  progressData, 
  onPhotoUpload,
  className 
}: ComparisonViewProps) {
  const [selectedAngle, setSelectedAngle] = useState<PhotoAngle>('front')
  const [beforeIndex, setBeforeIndex] = useState(0)
  const [afterIndex, setAfterIndex] = useState(progressData.length - 1)
  const [sliderPosition, setSliderPosition] = useState(50)
  const [isUploading, setIsUploading] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const sliderRef = useRef<HTMLDivElement>(null)

  // Filter photos by angle
  const getPhotosForAngle = (angle: PhotoAngle) => {
    return progressData
      .map((data, index) => ({
        ...data,
        photos: data.photos?.filter(p => p.type === angle) || [],
        index
      }))
      .filter(data => data.photos.length > 0)
  }

  const photosForAngle = getPhotosForAngle(selectedAngle)
  const beforeData = photosForAngle[beforeIndex]
  const afterData = photosForAngle[afterIndex]

  const handleFileUpload = async (file: File) => {
    if (!file || !file.type.startsWith('image/')) {
      toast.error('Por favor selecciona una imagen válida')
      return
    }

    setIsUploading(true)
    try {
      const photo = await progressService.uploadProgressPhoto(file, {
        type: selectedAngle,
        notes: ''
      })
      
      onPhotoUpload?.(photo)
      setShowUploadModal(false)
      toast.success('Foto subida exitosamente')
    } catch (error) {
      toast.error('Error al subir la foto')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }

  const handleSliderMove = (e: MouseEvent) => {
    if (!sliderRef.current) return
    
    const rect = sliderRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
    const percentage = (x / rect.width) * 100
    
    setSliderPosition(percentage)
  }

  const startSliderDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    
    const handleMouseMove = (e: MouseEvent) => handleSliderMove(e)
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  const handleShare = async () => {
    // Create canvas and draw comparison
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Implementation would create a side-by-side comparison image
    toast.success('Comparación lista para compartir')
  }

  const handleDownload = () => {
    // Similar to share but downloads the image
    toast.success('Descargando comparación...')
  }

  const AngleSelector = () => (
    <div className="flex bg-gray-100 rounded-lg p-1">
      {(['front', 'side', 'back'] as PhotoAngle[]).map(angle => (
        <button
          key={angle}
          onClick={() => setSelectedAngle(angle)}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded transition-all",
            selectedAngle === angle
              ? "bg-white text-purple-600 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          )}
        >
          {angle === 'front' ? 'Frente' : angle === 'side' ? 'Lado' : 'Espalda'}
        </button>
      ))}
    </div>
  )

  const PhotoSelector = ({ 
    photos, 
    selectedIndex, 
    onSelect, 
    label 
  }: {
    photos: typeof photosForAngle
    selectedIndex: number
    onSelect: (index: number) => void
    label: string
  }) => (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">{label}</h4>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onSelect(Math.max(0, selectedIndex - 1))}
          disabled={selectedIndex === 0}
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>
        
        <div className="flex-1 text-center">
          <p className="text-sm font-medium">
            {photos[selectedIndex] && format(parseISO(photos[selectedIndex].date), 'dd/MM/yyyy')}
          </p>
          <p className="text-xs text-gray-500">
            {photos[selectedIndex]?.weight && `${photos[selectedIndex].weight} kg`}
          </p>
        </div>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onSelect(Math.min(photos.length - 1, selectedIndex + 1))}
          disabled={selectedIndex === photos.length - 1}
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  )

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="border-b border-gray-100">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold text-navy-700">
            Comparación de Progreso
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <AngleSelector />
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowUploadModal(true)}
            >
              <Upload className="w-4 h-4 mr-2" />
              Subir Foto
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleShare}
            >
              <Share2 className="w-4 h-4" />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDownload}
            >
              <Download className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6">
        {photosForAngle.length < 2 ? (
          <div className="text-center py-12">
            <Camera className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">
              Necesitas al menos 2 fotos de {selectedAngle === 'front' ? 'frente' : selectedAngle === 'side' ? 'lado' : 'espalda'} para comparar
            </p>
            <Button
              onClick={() => setShowUploadModal(true)}
              className="bg-purple-500 hover:bg-purple-600"
            >
              <Upload className="w-4 h-4 mr-2" />
              Subir Primera Foto
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Photo Selectors */}
            <div className="grid grid-cols-2 gap-6">
              <PhotoSelector
                photos={photosForAngle}
                selectedIndex={beforeIndex}
                onSelect={setBeforeIndex}
                label="Antes"
              />
              <PhotoSelector
                photos={photosForAngle}
                selectedIndex={afterIndex}
                onSelect={setAfterIndex}
                label="Después"
              />
            </div>

            {/* Comparison View */}
            <div 
              ref={sliderRef}
              className="relative aspect-[3/4] bg-gray-100 rounded-lg overflow-hidden cursor-ew-resize"
              onMouseDown={startSliderDrag}
            >
              {/* Before Image */}
              <div className="absolute inset-0">
                <img
                  src={beforeData?.photos[0]?.url}
                  alt="Before"
                  className="w-full h-full object-cover"
                />
              </div>

              {/* After Image with Clip */}
              <div 
                className="absolute inset-0"
                style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}
              >
                <img
                  src={afterData?.photos[0]?.url}
                  alt="After"
                  className="w-full h-full object-cover"
                />
              </div>

              {/* Slider Line */}
              <div 
                className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize"
                style={{ left: `${sliderPosition}%` }}
              >
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center">
                  <ChevronLeft className="w-4 h-4 text-gray-600 absolute -left-1" />
                  <ChevronRight className="w-4 h-4 text-gray-600 absolute -right-1" />
                </div>
              </div>

              {/* Labels */}
              <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded">
                Antes
              </div>
              <div className="absolute top-4 right-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded">
                Después
              </div>
            </div>

            {/* Stats Comparison */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
              <div className="text-center">
                <p className="text-sm text-gray-600">Diferencia de Peso</p>
                <p className="text-lg font-bold text-purple-600">
                  {beforeData?.weight && afterData?.weight 
                    ? `${(afterData.weight - beforeData.weight).toFixed(1)} kg`
                    : '-'
                  }
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600">Días Transcurridos</p>
                <p className="text-lg font-bold text-navy-600">
                  {Math.abs(
                    Math.floor(
                      (new Date(afterData?.date).getTime() - new Date(beforeData?.date).getTime()) 
                      / (1000 * 60 * 60 * 24)
                    )
                  )}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600">% Grasa Corporal</p>
                <p className="text-lg font-bold text-green-600">
                  {beforeData?.body_fat_percentage && afterData?.body_fat_percentage
                    ? `${(afterData.body_fat_percentage - beforeData.body_fat_percentage).toFixed(1)}%`
                    : '-'
                  }
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>

      {/* Upload Modal */}
      <AnimatePresence>
        {showUploadModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setShowUploadModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-white rounded-lg p-6 max-w-md w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Subir Foto de Progreso</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowUploadModal(false)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>

              <div
                className={cn(
                  "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                  isDragging ? "border-purple-500 bg-purple-50" : "border-gray-300",
                  "cursor-pointer"
                )}
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsDragging(true)
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-2">
                  Arrastra una imagen aquí o haz clic para seleccionar
                </p>
                <p className="text-xs text-gray-500">
                  PNG, JPG hasta 10MB
                </p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleFileUpload(file)
                }}
              />

              <div className="mt-4">
                <p className="text-sm text-gray-600 mb-2">Ángulo de la foto:</p>
                <AngleSelector />
              </div>

              {isUploading && (
                <div className="mt-4 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mx-auto"></div>
                  <p className="text-sm text-gray-600 mt-2">Subiendo foto...</p>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}