<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { apiGet, apiPatch, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { useAuthStore } from '@/stores/auth'
import type { Announcement, ListResponse } from '@/types/content'

const authStore = useAuthStore()
const form = reactive({ id: '', title: '', content_html: '', is_pinned: false })
const data = ref<ListResponse<Announcement> | null>(null)
const message = ref('')
const error = ref('')
const submitting = ref(false)

async function load() { data.value = await apiGet('/announcements') }
onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '加载失败' }))

function edit(item: Announcement) {
  form.id = item.id
  form.title = item.title
  form.content_html = item.content_html
  form.is_pinned = item.is_pinned
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function reset() { form.id = ''; form.title = ''; form.content_html = ''; form.is_pinned = false }

async function save() {
  submitting.value = true
  error.value = ''
  message.value = ''
  try {
    const body = { title: form.title, content_html: form.content_html, is_pinned: form.is_pinned }
    if (form.id) {
      await apiPatch(`/admin/announcements/${form.id}`, body, authStore.token)
      message.value = '公告已更新。'
    } else {
      await apiPost('/admin/announcements', body, authStore.token)
      message.value = '公告已发布。'
    }
    reset()
    await load()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '保存失败'
  } finally { submitting.value = false }
}
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading"><p class="section-kicker">ANNOUNCEMENT MANAGEMENT</p><h1>平台公告</h1><p>发布规则、维护和平台信息；内容输出会经过安全清洗。</p></header>
    <div class="admin-editor-layout">
      <form class="content-form" @submit.prevent="save">
        <FormMessage v-if="message" type="success" :message="message" />
        <FormMessage v-if="error" :message="error" />
        <label><span>公告标题</span><input v-model.trim="form.title" maxlength="160" required /></label>
        <label><span>正文内容</span><RichTextEditor v-model="form.content_html" /></label>
        <label class="checkbox-field"><input v-model="form.is_pinned" type="checkbox" /><span>设为重要 / 置顶公告</span></label>
        <div class="form-actions"><button class="button primary" type="submit" :disabled="submitting">{{ form.id ? '保存修改' : '发布公告' }}</button><button v-if="form.id" class="button secondary" type="button" @click="reset">取消编辑</button></div>
      </form>
      <aside class="version-history"><h2>已发布公告</h2><ol><li v-for="item in data?.items" :key="item.id"><button type="button" @click="edit(item)"><strong>{{ item.is_pinned ? '置顶' : '公告' }}</strong><span>{{ item.title }}</span></button></li></ol></aside>
    </div>
  </div>
</template>
