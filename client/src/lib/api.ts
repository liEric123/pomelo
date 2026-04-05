import { loadSession } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

type JsonBody = Record<string, unknown> | unknown[]

export type ApiRequestOptions = Omit<RequestInit, 'body'> & {
  body?: BodyInit | JsonBody | null
}

export async function apiFetch<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { body, headers, ...init } = options
  const requestHeaders = new Headers(headers)

  // Auto-attach bearer token from session if present and not already set
  const session = loadSession()
  if (session?.access_token && !requestHeaders.has('Authorization')) {
    requestHeaders.set('Authorization', `Bearer ${session.access_token}`)
  }

  let resolvedBody: BodyInit | undefined

  if (body != null) {
    if (
      body instanceof FormData ||
      body instanceof URLSearchParams ||
      body instanceof Blob ||
      typeof body === 'string' ||
      body instanceof ArrayBuffer
    ) {
      resolvedBody = body
    } else {
      requestHeaders.set('Content-Type', 'application/json')
      resolvedBody = JSON.stringify(body)
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: requestHeaders,
    body: resolvedBody,
  })

  if (!response.ok) {
    const contentType = response.headers.get('Content-Type') ?? ''
    let errorDetail = ''

    if (contentType.includes('application/json')) {
      const payload = (await response.json()) as { detail?: string }
      errorDetail = payload.detail ?? ''
    } else {
      errorDetail = await response.text()
    }

    const detailSuffix = errorDetail ? `: ${errorDetail}` : ''
    throw new Error(
      `API request failed with status ${response.status}${detailSuffix}`,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('Content-Type') ?? ''

  if (contentType.includes('application/json')) {
    return (await response.json()) as T
  }

  return (await response.text()) as T
}

export { API_BASE_URL }
