<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  eyebrow?: string
  title: string
  description: string
}>()
</script>

<template>
  <div class="page-shell placeholder-page">
    <div class="placeholder-copy">
      <p class="section-kicker">{{ eyebrow ?? 'PHASE 0' }}</p>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
      <RouterLink class="text-link" to="/">← 返回首页</RouterLink>
    </div>
  </div>
</template>
