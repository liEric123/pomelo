export type AuthSession = {
  access_token: string
  role: 'candidate' | 'recruiter'
  candidate_id: number | null
  company_id: number | null
  email: string | null
}

const STORAGE_KEY = 'pomelo.auth'

export function loadSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AuthSession) : null
  } catch {
    return null
  }
}

export function saveSession(session: AuthSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

export function clearSession(): void {
  localStorage.removeItem(STORAGE_KEY)
}
