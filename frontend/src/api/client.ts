const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOptions extends RequestInit {
  token?: string
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers, ...requestOptions } = options
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers: {
      Accept: 'application/json',
      ...(requestOptions.body && !(requestOptions.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  })

  const responseBody = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof responseBody?.detail === 'string'
      ? responseBody.detail
      : 'The request could not be completed.'
    throw new ApiError(response.status, detail)
  }

  return responseBody as T
}

export async function apiBlobRequest(
  path: string,
  options: RequestOptions = {},
): Promise<{ blob: Blob; filename: string | null }> {
  const { token, headers, ...requestOptions } = options
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers: {
      Accept: 'text/csv',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  })

  if (!response.ok) {
    const responseBody = await response.json().catch(() => null)
    const detail = typeof responseBody?.detail === 'string'
      ? responseBody.detail
      : 'The request could not be completed.'
    throw new ApiError(response.status, detail)
  }

  const contentDisposition = response.headers.get('Content-Disposition')
  const filenameMatch = contentDisposition?.match(/filename="?([^";]+)"?/i)
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1] ?? null,
  }
}

export { API_BASE_URL }