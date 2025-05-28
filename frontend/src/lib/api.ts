import axios, { AxiosError, AxiosInstance } from 'axios'
import { ApiResponse } from '@/types'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    })

    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  private getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token')
    }
    return null
  }

  private setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
  }

  private clearToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }
  }

  async get<T>(url: string): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.get<T>(url)
      return {
        data: response.data,
        status: response.status,
      }
    } catch (error) {
      return this.handleError(error)
    }
  }

  async post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.post<T>(url, data)
      return {
        data: response.data,
        status: response.status,
      }
    } catch (error) {
      return this.handleError(error)
    }
  }

  async put<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.put<T>(url, data)
      return {
        data: response.data,
        status: response.status,
      }
    } catch (error) {
      return this.handleError(error)
    }
  }

  async delete<T>(url: string): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.delete<T>(url)
      return {
        data: response.data,
        status: response.status,
      }
    } catch (error) {
      return this.handleError(error)
    }
  }

  private handleError(error: unknown): ApiResponse<unknown> {
    if (axios.isAxiosError(error)) {
      return {
        error: error.response?.data?.error || error.message,
        message: error.response?.data?.message || 'An error occurred',
        status: error.response?.status || 500,
      }
    }
    return {
      error: 'An unexpected error occurred',
      message: error.message || 'Unknown error',
      status: 500,
    }
  }

  setAuthToken(token: string): void {
    this.setToken(token)
  }

  clearAuthToken(): void {
    this.clearToken()
  }
}

export const api = new ApiClient()