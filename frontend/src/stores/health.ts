import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { apiGet } from '@/api/client'
import type { HealthResponse } from '@/types/api'

export const useHealthStore = defineStore('health', () => {
  const health = ref<HealthResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isHealthy = computed(() => health.value?.status === 'ok' && health.value.database === 'ok')

  async function check(signal?: AbortSignal) {
    loading.value = true
    error.value = null
    try {
      health.value = await apiGet<HealthResponse>('/health', signal)
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return
      health.value = null
      error.value = '服务暂未连接'
    } finally {
      loading.value = false
    }
  }

  return { health, loading, error, isHealthy, check }
})
