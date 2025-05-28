export interface User {
  id: string
  email: string
  name: string
  avatar_url?: string
  created_at: string
  updated_at: string
  preferences?: UserPreferences
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  notifications: boolean
  language: string
  timezone: string
}

export interface Agent {
  id: string
  name: string
  description: string
  icon: string
  capabilities: string[]
  status: 'active' | 'inactive' | 'busy'
}

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  agent_id?: string
  created_at: string
  metadata?: MessageMetadata
}

export interface MessageMetadata {
  intent?: string
  confidence?: number
  processing_time?: number
  attachments?: Attachment[]
}

export interface Attachment {
  id: string
  type: 'image' | 'document' | 'audio' | 'video'
  url: string
  name: string
  size: number
}

export interface Session {
  id: string
  user_id: string
  created_at: string
  updated_at: string
  messages: Message[]
  active_agents: string[]
}

export interface BiometricData {
  id: string
  user_id: string
  type: 'heart_rate' | 'steps' | 'calories' | 'sleep' | 'weight' | 'body_fat'
  value: number
  unit: string
  source: string
  recorded_at: string
}

export interface WorkoutPlan {
  id: string
  user_id: string
  name: string
  description: string
  duration_weeks: number
  sessions_per_week: number
  exercises: Exercise[]
  created_by: string
  created_at: string
}

export interface Exercise {
  id: string
  name: string
  category: string
  muscle_groups: string[]
  sets: number
  reps: string
  rest_seconds: number
  notes?: string
  video_url?: string
}

export interface NutritionPlan {
  id: string
  user_id: string
  name: string
  calories_target: number
  macros: Macros
  meals: Meal[]
  created_by: string
  created_at: string
}

export interface Macros {
  protein: number
  carbs: number
  fats: number
  fiber: number
}

export interface Meal {
  id: string
  name: string
  time: string
  calories: number
  macros: Macros
  foods: Food[]
}

export interface Food {
  id: string
  name: string
  brand?: string
  quantity: number
  unit: string
  calories: number
  macros: Macros
}

export interface Progress {
  id: string
  user_id: string
  date: string
  weight?: number
  body_fat_percentage?: number
  measurements?: Measurements
  photos?: ProgressPhoto[]
  notes?: string
}

export interface Measurements {
  chest?: number
  waist?: number
  hips?: number
  biceps?: number
  thighs?: number
  neck?: number
  shoulders?: number
  forearms?: number
  calves?: number
}

export interface ProgressPhoto {
  id: string
  url: string
  thumbnail_url?: string
  type: 'front' | 'side' | 'back'
  created_at: string
  notes?: string
}

export interface Goal {
  id: string
  title: string
  description?: string
  target_value: number
  current_value: number
  unit: string
  target_date: string
  created_at: string
  status: 'active' | 'completed' | 'paused' | 'failed'
  category: 'weight' | 'body_fat' | 'muscle' | 'performance' | 'custom'
}

export interface Achievement {
  id: string
  title: string
  description: string
  icon: string
  category: string
  unlocked_at?: string
  progress?: number
  requirements?: string[]
  rarity: 'common' | 'rare' | 'epic' | 'legendary'
}

export interface ProgressStats {
  total_weight_lost?: number
  total_muscle_gained?: number
  body_fat_change?: number
  streak_days: number
  total_workouts: number
  total_achievements: number
  best_streak: number
  start_date: string
}

export interface Milestone {
  id: string
  title: string
  description: string
  date: string
  type: 'weight' | 'measurement' | 'performance' | 'habit' | 'custom'
  value?: number
  unit?: string
  celebrated: boolean
}

export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
  status: number
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}