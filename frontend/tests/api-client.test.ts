import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiPost } from '../src/api/client'

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
      message: 'QQ 号或密码错误',
      details: null,
      request_id: 'request-1',
    }), { status: 401 })))

    await expect(apiPost('/auth/login', {})).rejects.toMatchObject({
      status: 401,
      message: 'QQ 号或密码错误',
    })
  })
})
