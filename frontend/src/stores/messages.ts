import { defineStore } from 'pinia'
import { ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import type { UnreadCountResponse } from '@/types/message'

export const useMessageStore = defineStore('messages', () => {
  const unreadCount = ref(0)

  async function refresh(token: string | null) {
    if (!token) {
      unreadCount.value = 0
      return
    }
    const response = await apiGet<UnreadCountResponse>('/messages/unread-count', undefined, token)
    unreadCount.value = response.unread_count
  }

  async function markRead(messageId: string, token: string | null) {
    await apiPost(`/messages/${messageId}/read`, {}, token)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  async function markAllRead(token: string | null) {
    await apiPost('/messages/read-all', {}, token)
    unreadCount.value = 0
  }

  return { unreadCount, refresh, markRead, markAllRead }
})
