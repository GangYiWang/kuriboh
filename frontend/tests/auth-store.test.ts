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
})
