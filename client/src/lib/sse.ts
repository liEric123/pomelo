import { API_BASE_URL } from './api'

type SubscribeDashboardOptions = {
  withCredentials?: boolean
}

export function subscribeDashboard(
  options: SubscribeDashboardOptions = {},
): EventSource {
  return new EventSource(`${API_BASE_URL}/api/recruiter/stream`, options)
}
