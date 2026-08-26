<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { apiGet } from '@/api/client'
import type { Announcement, ListResponse } from '@/types/content'

const data = ref<ListResponse<Announcement> | null>(null)
const error = ref('')
onMounted(async () => {
  try { data.value = await apiGet('/announcements') }
  catch (caught) { error.value = caught instanceof Error ? caught.message : '公告加载失败' }
})
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long' }).format(new Date(value))
</script>

<template>
  <div class="page-shell content-list-page">
    <header class="page-heading"><h1>平台公告</h1><p>栗子杯规则、维护和运营通知。</p></header>
    <p v-if="error" class="form-message error">{{ error }}</p>
    <div v-else-if="data?.items.length" class="document-list">
      <RouterLink v-for="item in data.items" :key="item.id" :to="`/announcements/${item.id}`" class="document-row">
        <span class="document-index">{{ item.is_pinned ? '置顶' : formatDate(item.published_at).slice(5) }}</span>
        <span><strong>{{ item.title }}</strong><small>{{ formatDate(item.published_at) }}</small></span><i>→</i>
      </RouterLink>
    </div>
    <div v-else class="empty-content"><h2>暂无公告</h2><p>管理员发布公告后将在这里展示。</p></div>
  </div>
</template>
