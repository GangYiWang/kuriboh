<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

import { useHealthStore } from '@/stores/health'

const healthStore = useHealthStore()
const controller = new AbortController()

onMounted(() => healthStore.check(controller.signal))
onBeforeUnmount(() => controller.abort())
</script>

<template>
  <div class="system-status" role="status" aria-live="polite">
    <span :class="['status-dot', { healthy: healthStore.isHealthy }]" aria-hidden="true" />
    <span v-if="healthStore.loading">正在连接服务</span>
    <span v-else-if="healthStore.isHealthy">前后端服务已连接</span>
    <span v-else>{{ healthStore.error ?? '等待服务状态' }}</span>
  </div>
</template>
