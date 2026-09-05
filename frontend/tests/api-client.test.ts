import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiDelete, apiPost } from '../src/api/client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API client error handling', () => {
  it('reports an unavailable backend without exposing a JSON parsing error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 502 })))

    await expect(apiPost('/auth/login', {})).rejects.toMatchObject({
      status: 502,
      message: '后端服务暂不可用，请确认 API 服务已启动。',
    })
  })

  it('preserves the structured error returned by the API', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      code: 'INVALID_CREDENTIALS',
      message: '手机号、QQ 号或密码错误',
      details: null,
      request_id: 'request-1',
    }), { status: 401 })))

    await expect(apiPost('/auth/login', {})).rejects.toMatchObject({
      status: 401,
      message: '手机号、QQ 号或密码错误',
    })
  })

  it('sends delete requests and accepts an empty 204 response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiDelete('/admin/tournaments/example', 'token')).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith('/api/admin/tournaments/example', expect.objectContaining({
      method: 'DELETE',
    }))
  })
})
