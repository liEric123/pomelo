import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/auth-context'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

export function RequireCandidate({ children }: { children: ReactNode }) {
  const { isAuthenticated, isCandidate } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (!isCandidate) {
    return <Navigate to="/recruiter/dashboard" replace />
  }

  return <>{children}</>
}

export function RequireRecruiter({ children }: { children: ReactNode }) {
  const { isAuthenticated, isRecruiter } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (!isRecruiter) {
    return <Navigate to="/candidate/feed" replace />
  }

  return <>{children}</>
}
