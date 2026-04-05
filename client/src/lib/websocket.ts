import { loadSession } from './auth'
import { API_BASE_URL } from './api'

export type InterviewMessage = Record<string, unknown>

type ConnectInterviewOptions = {
  token?: string         // explicit override; falls back to session token
  onMessage?: (message: InterviewMessage) => void
  onError?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
}

const MAX_RETRIES = 3

function buildInterviewUrl(matchId: string, token: string | null | undefined): string {
  const base = API_BASE_URL || window.location.origin
  const url = new URL(`/api/interviews/${matchId}/ws`, base)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  if (token) {
    url.searchParams.set('token', token)
  }
  return url.toString()
}

export function connectInterview(
  matchId: string,
  options: ConnectInterviewOptions = {},
): WebSocket {
  const session = loadSession()
  const token = options.token ?? session?.access_token

  let retries = 0
  let manuallyClosed = false
  let socket = createSocket()

  function createSocket() {
    const nextSocket = new WebSocket(buildInterviewUrl(matchId, token))

    nextSocket.addEventListener('message', (event) => {
      try {
        const parsed = JSON.parse(event.data) as InterviewMessage
        options.onMessage?.(parsed)
      } catch (error) {
        console.error('Failed to parse interview message', error)
      }
    })

    nextSocket.addEventListener('error', (event) => {
      options.onError?.(event)
    })

    nextSocket.addEventListener('close', (event) => {
      options.onClose?.(event)

      if (manuallyClosed || retries >= MAX_RETRIES) {
        return
      }

      retries += 1
      window.setTimeout(() => {
        socket = createSocket()
      }, retries * 1000)
    })

    const originalClose = nextSocket.close.bind(nextSocket)
    nextSocket.close = ((code?: number, reason?: string) => {
      manuallyClosed = true
      originalClose(code, reason)
    }) as WebSocket['close']

    return nextSocket
  }

  return socket
}
