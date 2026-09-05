import type { ApiErrorBody } from '@/types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody,
  ) {
    super(body.message)
  }
}

interface RequestOptions extends RequestInit {
  token?: string | null
}

function fallbackErrorBody(status: number, responseText = ''): ApiErrorBody {
  const serviceUnavailable = status === 0 || [502, 503, 504].includes(status)
  return {
    code: serviceUnavailable ? 'API_UNAVAILABLE' : `HTTP_${status}`,
    message: serviceUnavailable
      ? '后端服务暂不可用，请确认 API 服务已启动。'
      : `请求失败（HTTP ${status}）。`,
    details: responseText || null,
    request_id: '',
  }
}

function parseJsonBody(text: string): unknown | null {
  if (!text.trim()) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return null
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return Boolean(
    value
      && typeof value === 'object'
      && 'message' in value
      && typeof value.message === 'string',
  )
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers: suppliedHeaders, ...requestOptions } = options
  const headers = new Headers(suppliedHeaders)
  headers.set('Accept', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (requestOptions.body && !(requestOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      headers,
    })
  } catch {
    const body = fallbackErrorBody(0)
    throw new ApiError(0, body)
  }

  const responseText = response.status === 204 ? '' : await response.text()
  const parsedBody = parseJsonBody(responseText)

  if (!response.ok) {
    const body = isApiErrorBody(parsedBody)
      ? parsedBody
      : fallbackErrorBody(response.status, responseText)
    throw new ApiError(response.status, body)
  }

  if (response.status === 204) return undefined as T
  if (parsedBody === null) {
    throw new ApiError(response.status, {
      code: 'INVALID_API_RESPONSE',
      message: '后端返回了无法识别的响应，请稍后重试。',
      details: responseText || null,
      request_id: '',
    })
  }
  return parsedBody as T
}

export function apiGet<T>(path: string, signal?: AbortSignal, token?: string | null): Promise<T> {
  return apiRequest<T>(path, { signal, token })
}

export function apiPost<T>(path: string, body: unknown, token?: string | null): Promise<T> {
  return apiRequest<T>(path, { method: 'POST', body: JSON.stringify(body), token })
}

export function apiPostForm<T>(path: string, body: FormData, token?: string | null): Promise<T> {
  return apiRequest<T>(path, { method: 'POST', body, token })
}

export function apiPatch<T>(path: string, body: unknown, token?: string | null): Promise<T> {
  return apiRequest<T>(path, { method: 'PATCH', body: JSON.stringify(body), token })
}

export function apiDelete<T = void>(path: string, token?: string | null): Promise<T> {
  return apiRequest<T>(path, { method: 'DELETE', token })
}
