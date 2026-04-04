import { API_BASE_URL } from './api'

export type InterviewMessage = Record<string, unknown>

type ConnectInterviewOptions = {
  onMessage?: (message: InterviewMessage) => void
  onError?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
}

const MAX_RETRIES = 3

function toWebSocketUrl(path: string) {
  const url = new URL(path, API_BASE_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

export function connectInterview(
  matchId: string,
  options: ConnectInterviewOptions = {},
): WebSocket {
  let retries = 0
  let manuallyClosed = false
  let socket = createSocket()

  function createSocket() {
    const nextSocket = new WebSocket(
      toWebSocketUrl(`/api/interview/${matchId}`),
    )

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
