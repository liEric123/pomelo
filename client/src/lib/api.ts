const API_BASE_URL = 'http://localhost:8000'

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
    throw new Error(`API request failed with status ${response.status}`)
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
