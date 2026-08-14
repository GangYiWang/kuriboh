<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { apiGet } from '@/api/client'
import type { BanlistVersion, ListResponse } from '@/types/content'

const data = ref<ListResponse<BanlistVersion> | null>(null)
const error = ref('')

onMounted(async () => {
  try { data.value = await apiGet('/banlists') }
  catch (caught) { error.value = caught instanceof Error ? caught.message : '禁卡表加载失败' }
})

const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value))
</script>

<template>
  <div class="page-shell content-list-page">
    <header class="page-heading split-heading">
      <div><p class="section-kicker">BANLIST ARCHIVE</p><h1>禁卡表</h1><p>查看当前版本与历史版本，已发布内容永久保留。</p></div>
      <span v-if="data?.items.length" class="current-version">当前 {{ data.items[0].version }}</span>
    </header>
    <p v-if="error" class="form-message error">{{ error }}</p>
    <div v-else-if="data?.items.length" class="document-list">
      <RouterLink v-for="(item, index) in data.items" :key="item.id" :to="`/banlists/${item.id}`" class="document-row">
        <span class="document-index">{{ item.version }}</span>
        <span><strong>{{ item.title }}</strong><small>{{ formatDate(item.published_at) }} 发布</small></span>
        <span v-if="index === 0" class="status-text">当前版本</span><i>→</i>
      </RouterLink>
    </div>
    <div v-else class="empty-content"><h2>暂无禁卡表</h2><p>管理员发布首个版本后将在这里展示。</p></div>
  </div>
</template>
