import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../src/stores/auth'

beforeEach(() => {
  const values = new Map([['lizibei_access_token', 'test-token']])
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  })
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('authentication profile loading', () => {
  it('shares an in-flight profile request between the app header and route guard', async () => {
    let resolveFetch!: (response: Response) => void
    const pendingResponse = new Promise<Response>((resolve) => {
      resolveFetch = resolve
    })
    const fetchMock = vi.fn().mockReturnValue(pendingResponse)
    vi.stubGlobal('fetch', fetchMock)

    const authStore = useAuthStore()
    const headerRequest = authStore.ensureProfile()
    const guardRequest = authStore.ensureProfile()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    resolveFetch(new Response(JSON.stringify({
      id: 'admin-1',
      phone_number: '13800138000',
      qq_number: '10000002',
      nickname: '测试管理员',
      role: 'TOURNAMENT_ADMIN',
      qq_bound: false,
      created_at: '2026-08-13T00:00:00Z',
    }), { status: 200 }))

    await Promise.all([headerRequest, guardRequest])
    expect(authStore.isAuthenticated).toBe(true)
    expect(authStore.isAdmin).toBe(true)
  })

  it('sends compatible phone and QQ identifiers to the authentication API', async () => {
    const session = {
      access_token: 'new-token',
      token_type: 'bearer',
      user: {
        id: 'player-1',
        phone_number: '13800138000',
        qq_number: null,
        nickname: '测试选手',
        role: 'PLAYER',
        qq_bound: false,
        created_at: '2026-08-24T00:00:00Z',
      },
    }
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(
      new Response(JSON.stringify(session), { status: 200 }),
    ))
    vi.stubGlobal('fetch', fetchMock)

    const authStore = useAuthStore()
    await authStore.login('13800138000', 'password123')
    await authStore.register({
      identifier_type: 'QQ',
      identifier: '123456789',
      nickname: '测试选手',
      password: 'password123',
      confirm_password: 'password123',
    })

    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      identifier: '13800138000',
      password: 'password123',
    })
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toEqual({
      identifier_type: 'QQ',
      identifier: '123456789',
      nickname: '测试选手',
      password: 'password123',
      confirm_password: 'password123',
    })
  })
})
