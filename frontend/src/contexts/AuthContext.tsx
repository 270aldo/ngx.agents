'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { User } from '@/types'
import { api } from '@/lib/api'
import { supabase } from '@/lib/supabase'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => Promise<void>
  resetPassword: (email: string) => Promise<void>
  updateProfile: (data: Partial<User>) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    checkUser()
    
    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (session?.user) {
          await fetchUserProfile(session.user.id)
        } else {
          setUser(null)
        }
        setLoading(false)
      }
    )

    return () => {
      authListener.subscription.unsubscribe()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function checkUser() {
    try {
      const { data: { user: authUser } } = await supabase.auth.getUser()
      if (authUser) {
        await fetchUserProfile(authUser.id)
      }
    } catch (error) {
      console.error('Error checking user:', error)
    } finally {
      setLoading(false)
    }
  }

  async function fetchUserProfile(userId: string) {
    try {
      const response = await api.get<User>(`/users/${userId}`)
      if (response.data) {
        setUser(response.data)
      }
    } catch (error) {
      console.error('Error fetching user profile:', error)
    }
  }

  async function login(email: string, password: string) {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      
      if (error) throw error
      
      if (data.user) {
        await fetchUserProfile(data.user.id)
        api.setAuthToken(data.session?.access_token || '')
        router.push('/dashboard')
      }
    } catch (error: unknown) {
      throw new Error((error as Error).message || 'Failed to login')
    }
  }

  async function register(email: string, password: string, name: string) {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { name },
        },
      })
      
      if (error) throw error
      
      if (data.user) {
        // Create user profile in backend
        await api.post('/users', {
          id: data.user.id,
          email,
          name,
        })
        
        await fetchUserProfile(data.user.id)
        api.setAuthToken(data.session?.access_token || '')
        router.push('/onboarding')
      }
    } catch (error: unknown) {
      throw new Error((error as Error).message || 'Failed to register')
    }
  }

  async function logout() {
    try {
      await supabase.auth.signOut()
      api.clearAuthToken()
      setUser(null)
      router.push('/')
    } catch (error: unknown) {
      throw new Error((error as Error).message || 'Failed to logout')
    }
  }

  async function resetPassword(email: string) {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      })
      
      if (error) throw error
    } catch (error: unknown) {
      throw new Error((error as Error).message || 'Failed to reset password')
    }
  }

  async function updateProfile(data: Partial<User>) {
    if (!user) return
    
    try {
      const response = await api.put<User>(`/users/${user.id}`, data)
      if (response.data) {
        setUser(response.data)
      }
    } catch (error: unknown) {
      throw new Error((error as Error).message || 'Failed to update profile')
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        resetPassword,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}