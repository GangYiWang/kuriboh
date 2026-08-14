import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import type { TokenResponse, User } from '@/types/auth'
import { useMessageStore } from '@/stores/messages'

const TOKEN_KEY = 'lizibei_access_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(null)
  const loading = ref(false)
  let profileRequest: Promise<void> | null = null
  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'TOURNAMENT_ADMIN')

  function acceptSession(session: TokenResponse) {
    token.value = session.access_token
    user.value = session.user
    localStorage.setItem(TOKEN_KEY, session.access_token)
  }

  async function login(qqNumber: string, password: string) {
    acceptSession(await apiPost<TokenResponse>('/auth/login', { qq_number: qqNumber, password }))
  }

  async function register(payload: {
    qq_number: string
    nickname: string
    password: string
    confirm_password: string
  }) {
    acceptSession(await apiPost<TokenResponse>('/auth/register', payload))
  }

  async function ensureProfile() {
    if (!token.value || user.value) return
    if (profileRequest) return profileRequest

    loading.value = true
    profileRequest = (async () => {
      try {
        user.value = await apiGet<User>('/auth/me', undefined, token.value)
      } catch {
        logout()
      } finally {
        loading.value = false
        profileRequest = null
      }
    })()
    return profileRequest
  }

  async function changePassword(currentPassword: string, newPassword: string, confirmPassword: string) {
    await apiPost<void>('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }, token.value)
  }

  async function bindQq(bindingToken: string) {
    user.value = await apiPost<User>('/auth/qq/bind', { binding_token: bindingToken }, token.value)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    useMessageStore().unreadCount = 0
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    isAdmin,
    acceptSession,
    login,
    register,
    ensureProfile,
    changePassword,
    bindQq,
    logout,
  }
})
