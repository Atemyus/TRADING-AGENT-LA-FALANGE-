'use client'

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { getApiBaseUrl, getErrorMessageFromPayload, parseJsonResponse } from '@/lib/http'

const API_URL = getApiBaseUrl()

type TokenResponse = {
  access_token: string
  refresh_token: string
}

interface User {
  id: number
  email: string
  username: string
  full_name: string | null
  avatar_url: string | null
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  created_at: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

interface RegisterData {
  email: string
  username: string
  password: string
  full_name?: string
  license_key: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  const getAccessToken = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token')
    }
    return null
  }

  const getRefreshToken = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('refresh_token')
    }
    return null
  }

  const setTokens = (accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
  }

  const clearTokens = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  const refreshAccessToken = async (): Promise<boolean> => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) return false

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        throw new Error('Token refresh failed')
      }

      const data = await parseJsonResponse<TokenResponse>(response)
      if (!data?.access_token || !data?.refresh_token) {
        throw new Error('Invalid token refresh response')
      }

      setTokens(data.access_token, data.refresh_token)
      return true
    } catch {
      clearTokens()
      return false
    }
  }

  const fetchUser = useCallback(async () => {
    const accessToken = getAccessToken()
    if (!accessToken) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (response.status === 401) {
        // Try to refresh token
        const refreshed = await refreshAccessToken()
        if (refreshed) {
          // Retry with new token
          const newToken = getAccessToken()
          const retryResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
            headers: {
              Authorization: `Bearer ${newToken}`,
            },
          })
          if (retryResponse.ok) {
            const data = await parseJsonResponse<User>(retryResponse)
            setUser(data)
          } else {
            setUser(null)
            clearTokens()
          }
        } else {
          setUser(null)
          clearTokens()
        }
      } else if (response.ok) {
        const data = await parseJsonResponse<User>(response)
        setUser(data)
      } else {
        setUser(null)
        clearTokens()
      }
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/api/v1/auth/login/json`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    const data = await parseJsonResponse<TokenResponse>(response)

    if (!response.ok) {
      throw new Error(getErrorMessageFromPayload(data, 'Login failed'))
    }

    if (!data?.access_token || !data?.refresh_token) {
      throw new Error('Invalid login response from server')
    }

    setTokens(data.access_token, data.refresh_token)
    await fetchUser()
    router.push('/dashboard')
  }

  const register = async (registerData: RegisterData) => {
    const response = await fetch(`${API_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: registerData.email,
        username: registerData.username,
        password: registerData.password,
        full_name: registerData.full_name || null,
        license_key: registerData.license_key,
      }),
    })

    const data = await parseJsonResponse<Record<string, unknown>>(response)

    if (!response.ok) {
      throw new Error(getErrorMessageFromPayload(data, 'Registration failed'))
    }

    // Auto-login after registration
    await login(registerData.email, registerData.password)
  }

  const logout = () => {
    clearTokens()
    setUser(null)
    router.push('/login')
  }

  const refreshUser = async () => {
    await fetchUser()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
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
