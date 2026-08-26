<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { apiGet } from '@/api/client'
import type { Announcement } from '@/types/content'

const route = useRoute()
const item = ref<Announcement | null>(null)
const error = ref('')
onMounted(async () => {
  try { item.value = await apiGet(`/announcements/${route.params.id}`) }
  catch (caught) { error.value = caught instanceof Error ? caught.message : '公告加载失败' }
})
</script>

<template>
  <div class="page-shell article-page">
    <RouterLink class="back-link-light" to="/announcements">← 返回平台公告</RouterLink>
    <p v-if="error" class="form-message error">{{ error }}</p>
    <article v-else-if="item">
      <header class="article-heading"><h1>{{ item.title }}</h1><time>{{ new Date(item.published_at).toLocaleString('zh-CN') }} 发布</time></header>
      <div class="rich-content article-body" v-html="item.content_html" />
    </article>
  </div>
</template>
