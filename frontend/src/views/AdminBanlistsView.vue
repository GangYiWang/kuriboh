<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { useAuthStore } from '@/stores/auth'
import type { BanlistVersion, ListResponse } from '@/types/content'

const authStore = useAuthStore()
const title = ref('')
const content = ref('')
const data = ref<ListResponse<BanlistVersion> | null>(null)
const message = ref('')
const error = ref('')
const submitting = ref(false)

async function load() { data.value = await apiGet('/banlists') }
onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '加载失败' }))

async function publish() {
  submitting.value = true
  error.value = ''
  message.value = ''
  try {
    const item = await apiPost<BanlistVersion>('/admin/banlists', { title: title.value, content_html: content.value }, authStore.token)
    message.value = `${item.version} 已发布。`
    title.value = ''
    content.value = ''
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '发布失败'
  } finally { submitting.value = false }
}
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading split-heading"><div><p class="section-kicker">BANLIST MANAGEMENT</p><h1>禁卡表版本</h1><p>发布后自动生成下一版本，历史版本不会覆盖或删除。</p></div><span class="current-version">下一版本 {{ data?.items[0] ? (data.items[0].minor_version === 9 ? `V${data.items[0].major_version + 1}.0` : `V${data.items[0].major_version}.${data.items[0].minor_version + 1}`) : 'V1.0' }}</span></header>
    <div class="admin-editor-layout">
      <form class="content-form" @submit.prevent="publish">
        <FormMessage v-if="message" type="success" :message="message" />
        <FormMessage v-if="error" :message="error" />
        <label><span>版本标题</span><input v-model.trim="title" maxlength="120" required /></label>
        <label><span>正文内容</span><RichTextEditor v-model="content" /></label>
        <button class="button primary" type="submit" :disabled="submitting">{{ submitting ? '正在发布…' : '发布新版本' }}</button>
      </form>
      <aside class="version-history"><h2>版本历史</h2><ol><li v-for="item in data?.items" :key="item.id"><strong>{{ item.version }}</strong><span>{{ item.title }}</span></li></ol></aside>
    </div>
  </div>
</template>
