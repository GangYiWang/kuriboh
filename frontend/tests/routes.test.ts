import { describe, expect, it } from 'vitest'

import { routes } from '../src/router/routes'

describe('formal route skeleton', () => {
  it('includes the public and administration entry points from the V1 baseline', () => {
    const paths = routes.map((route) => route.path)

    expect(paths).toEqual(expect.arrayContaining([
      '/',
      '/login',
      '/register',
      '/tournaments',
      '/tournaments/:id',
      '/tournaments/:id/matches',
      '/tournaments/:id/results',
      '/reports',
      '/reports/:id',
      '/announcements',
      '/messages',
      '/profile',
      '/my-tournaments',
      '/admin',
      '/admin/messages',
      '/admin/audit',
      '/banlists/:id',
      '/login/qq/callback',
    ]))
  })

  it('protects personal and administration routes at the router metadata boundary', () => {
    const byPath = new Map(routes.map((route) => [route.path, route]))

    expect(byPath.get('/profile')?.meta?.requiresAuth).toBe(true)
    expect(byPath.get('/messages')?.meta?.requiresAuth).toBe(true)
    expect(byPath.get('/admin')?.meta?.requiresAdmin).toBe(true)
    expect(byPath.get('/admin/banlists')?.meta?.requiresAdmin).toBe(true)
    expect(byPath.get('/admin/tournaments')?.meta?.requiresAdmin).toBe(true)
    expect(byPath.get('/admin/tournaments/:id/:section(settings|registrations|matches|playoffs|decks-report|notifications|audit)')?.meta?.requiresAdmin).toBe(true)
    expect(byPath.get('/admin/messages')?.meta?.requiresAdmin).toBe(true)
    expect(byPath.get('/admin/audit')?.meta?.requiresAdmin).toBe(true)
    expect(byPath.get('/announcements')?.meta?.requiresAuth).not.toBe(true)
    expect(byPath.get('/reports')?.meta?.requiresAuth).not.toBe(true)
    expect(byPath.get('/reports/:id')?.meta?.requiresAuth).not.toBe(true)
  })
})
