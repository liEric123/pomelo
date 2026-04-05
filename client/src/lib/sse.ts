import { loadSession } from './auth'
import { API_BASE_URL } from './api'

type SubscribeDashboardOptions = {
  path: string           // e.g. /api/interviews/{matchId}/stream
  token?: string         // explicit override; falls back to session token
  withCredentials?: boolean
}

export function subscribeDashboard(
  options: SubscribeDashboardOptions,
): EventSource {
  const { path, withCredentials } = options

  // EventSource cannot send Authorization headers — token goes in query param
  const session = loadSession()
  const token = options.token ?? session?.access_token

  const separator = path.includes('?') ? '&' : '?'
  const fullPath = token
    ? `${path}${separator}token=${encodeURIComponent(token)}`
    : path

  return new EventSource(`${API_BASE_URL}${fullPath}`, { withCredentials })
}
