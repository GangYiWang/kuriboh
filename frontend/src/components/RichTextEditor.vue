<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { apiRequest } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { ImageUploadResponse } from '@/types/content'

const model = defineModel<string>({ required: true })
const authStore = useAuthStore()
const editor = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref('')

function renderModel(value: string) {
  if (editor.value && editor.value.innerHTML !== value) editor.value.innerHTML = value
}

onMounted(() => renderModel(model.value))
watch(model, renderModel)

function syncContent() {
  model.value = editor.value?.innerHTML ?? ''
}

function command(name: string, value?: string) {
  editor.value?.focus()
  document.execCommand(name, false, value)
  syncContent()
}

async function upload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadError.value = ''
  const form = new FormData()
  form.append('image', file)
  try {
    const result = await apiRequest<ImageUploadResponse>('/admin/uploads/images', {
      method: 'POST',
      body: form,
      token: authStore.token,
    })
    command('insertImage', result.url)
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : '图片上传失败'
  } finally {
    input.value = ''
  }
}
</script>

<template>
  <div class="rich-editor">
    <div class="editor-toolbar" aria-label="富文本工具栏">
      <button type="button" @click="command('formatBlock', 'h2')">标题</button>
      <button type="button" @click="command('formatBlock', 'p')">正文</button>
      <button type="button" @click="command('bold')">加粗</button>
      <button type="button" @click="command('insertUnorderedList')">列表</button>
      <button type="button" @click="fileInput?.click()">插入图片</button>
      <input ref="fileInput" class="visually-hidden" type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" @change="upload" />
    </div>
    <div
      ref="editor"
      class="editor-surface rich-content"
      contenteditable="true"
      role="textbox"
      aria-multiline="true"
      data-placeholder="输入正文，可使用上方工具添加标题、列表和图片"
      @input="syncContent"
    />
    <p v-if="uploadError" class="field-error">{{ uploadError }}</p>
  </div>
</template>
