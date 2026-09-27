import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getCurrentUser, loginRequest } from '../api/auth'
import type { ApiError } from '../api/client'
import type { CurrentUser, LoginRequest } from '../types/auth'

const TOKEN_KEY = 'fleet_telemetry_access_token'
const EMAIL_KEY = 'fleet_telemetry_login_email'

interface AuthContextValue {
  token: string | null
  currentUser: CurrentUser | null
  isAuthenticated: boolean
  isInitializing: boolean
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [isInitializing, setIsInitializing] = useState(Boolean(token))

  useEffect(() => {
    if (!token) {
      setIsInitializing(false)
      return
    }

    let active = true
    getCurrentUser(token)
      .then((profile) => {
        if (!active) return
        setCurrentUser({
          ...profile,
          email: localStorage.getItem(EMAIL_KEY) ?? undefined,
        })
      })
      .catch((error: unknown) => {
        if (!active) return
        if ((error as ApiError).status === 401 || error instanceof Error) {
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(EMAIL_KEY)
          setToken(null)
          setCurrentUser(null)
        }
      })
      .finally(() => {
        if (active) setIsInitializing(false)
      })

    return () => {
      active = false
    }
  }, [token])

  async function login(credentials: LoginRequest) {
    const session = await loginRequest(credentials)
    const profile = await getCurrentUser(session.access_token)
    localStorage.setItem(TOKEN_KEY, session.access_token)
    localStorage.setItem(EMAIL_KEY, credentials.email)
    setCurrentUser({ ...profile, email: credentials.email })
    setToken(session.access_token)
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
    setToken(null)
    setCurrentUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        currentUser,
        isAuthenticated: Boolean(token && currentUser),
        isInitializing,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}