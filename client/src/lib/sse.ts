import { API_BASE_URL } from './api'

type SubscribeDashboardOptions = {
  withCredentials?: boolean
  path?: string
}

export function subscribeDashboard(
  options: SubscribeDashboardOptions = {},
): EventSource {
  const { path = '/api/recruiter/stream', withCredentials } = options

  return new EventSource(`${API_BASE_URL}${path}`, { withCredentials })
}
