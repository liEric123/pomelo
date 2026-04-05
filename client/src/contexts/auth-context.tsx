import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from 'react'
import {
  clearSession,
  loadSession,
  saveSession,
  type AuthSession,
} from '../lib/auth'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

type AuthContextValue = {
  session: AuthSession | null
  isAuthenticated: boolean
  isCandidate: boolean
  isRecruiter: boolean
  login: (email: string, password: string) => Promise<AuthSession>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => loadSession())

  const login = useCallback(
    async (email: string, password: string): Promise<AuthSession> => {
      const form = new FormData()
      form.append('email', email)
      form.append('password', password)

      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        body: form,
      })

      if (!res.ok) {
        const data = (await res.json().catch(() => ({}))) as { detail?: string }
        throw new Error(data.detail ?? 'Invalid email or password.')
      }

      const data = (await res.json()) as {
        access_token: string
        role: 'candidate' | 'recruiter'
        candidate_id: number | null
        company_id: number | null
      }

      const newSession: AuthSession = {
        access_token: data.access_token,
        role: data.role,
        candidate_id: data.candidate_id,
        company_id: data.company_id,
        email,
      }

      saveSession(newSession)
      setSession(newSession)
      return newSession
    },
    [],
  )

  const logout = useCallback(() => {
    clearSession()
    setSession(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        session,
        isAuthenticated: session !== null,
        isCandidate: session?.role === 'candidate',
        isRecruiter: session?.role === 'recruiter',
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
