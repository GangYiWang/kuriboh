<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiGet, apiPatch, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { useAuthStore } from '@/stores/auth'
import type { BanlistVersion, ListResponse } from '@/types/content'

const authStore = useAuthStore()
const editingId = ref('')
const editingVersion = ref('')
const title = ref('')
const content = ref('')
const data = ref<ListResponse<BanlistVersion> | null>(null)
const message = ref('')
const error = ref('')
const submitting = ref(false)
const nextVersion = computed(() => {
  const latest = data.value?.items[0]
  if (!latest) return 'V1.0'
  return latest.minor_version === 9
    ? `V${latest.major_version + 1}.0`
    : `V${latest.major_version}.${latest.minor_version + 1}`
})

async function load() { data.value = await apiGet('/banlists') }
onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '加载失败' }))

function edit(item: BanlistVersion) {
  editingId.value = item.id
  editingVersion.value = item.version
  title.value = item.title
  content.value = item.content_html
  message.value = ''
  error.value = ''
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function resetEditor() {
  editingId.value = ''
  editingVersion.value = ''
  title.value = ''
  content.value = ''
  error.value = ''
}

async function save() {
  submitting.value = true
  error.value = ''
  message.value = ''
  try {
    const body = { title: title.value, content_html: content.value }
    const item = editingId.value
      ? await apiPatch<BanlistVersion>(`/admin/banlists/${editingId.value}`, body, authStore.token)
      : await apiPost<BanlistVersion>('/admin/banlists', body, authStore.token)
    message.value = editingId.value ? `${item.version} 已更新。` : `${item.version} 已发布。`
    resetEditor()
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : (editingId.value ? '更新失败' : '发布失败')
  } finally { submitting.value = false }
}
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading split-heading"><div><p class="section-kicker">BANLIST MANAGEMENT</p><h1>禁卡表版本</h1><p>发布新版本或点击历史版本修改内容；版本号保持不变，历史版本不会删除。</p></div><span class="current-version">{{ editingId ? `正在修改 ${editingVersion}` : `下一版本 ${nextVersion}` }}</span></header>
    <div class="admin-editor-layout">
      <form class="content-form" @submit.prevent="save">
        <FormMessage v-if="message" type="success" :message="message" />
        <FormMessage v-if="error" :message="error" />
        <label><span>版本标题</span><input v-model.trim="title" maxlength="120" required /></label>
        <label><span>正文内容</span><RichTextEditor v-model="content" /></label>
        <div class="form-actions"><button class="button primary" type="submit" :disabled="submitting">{{ submitting ? (editingId ? '正在保存…' : '正在发布…') : (editingId ? '保存修改' : '发布新版本') }}</button><button v-if="editingId" class="button secondary" type="button" :disabled="submitting" @click="resetEditor">取消修改</button></div>
      </form>
      <aside class="version-history"><h2>版本历史</h2><ol><li v-for="item in data?.items" :key="item.id"><button type="button" :disabled="submitting" @click="edit(item)"><strong>{{ item.version }}</strong><span>{{ item.title }}</span></button></li></ol></aside>
    </div>
  </div>
</template>
