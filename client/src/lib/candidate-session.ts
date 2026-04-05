const CANDIDATE_ID_STORAGE_KEY = 'pomelo.candidateId'

export function getStoredCandidateId() {
  if (typeof window === 'undefined') {
    return null
  }

  const rawValue = window.localStorage.getItem(CANDIDATE_ID_STORAGE_KEY)
  if (!rawValue) {
    return null
  }

  const parsedValue = Number.parseInt(rawValue, 10)
  return Number.isNaN(parsedValue) ? null : parsedValue
}

export function setStoredCandidateId(candidateId: number) {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(CANDIDATE_ID_STORAGE_KEY, String(candidateId))
}
