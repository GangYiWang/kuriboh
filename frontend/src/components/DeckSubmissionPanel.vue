<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { ApiError, apiGet, apiPostForm } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import type { DeckSubmission } from '@/types/report'
import { deckPlacementText, deckStatusText } from '@/types/report'

const props = defineProps<{ tournamentId: string; token: string }>()
const submission = ref<DeckSubmission | null>(null)
const eligible = ref<boolean | null>(null)
const selectedFile = ref<File | null>(null)
const busy = ref(false)
const error = ref('')
const message = ref('')

async function load() {
  try {
    submission.value = await apiGet<DeckSubmission>(
      `/tournaments/${props.tournamentId}/deck-submission/me`, undefined, props.token,
    )
    eligible.value = true
  } catch (caught) {
    if (caught instanceof ApiError && caught.body.code === 'NOT_FINAL_FOUR') {
      eligible.value = false
      return
    }
    eligible.value = null
    error.value = caught instanceof Error ? caught.message : '卡组提交状态加载失败'
  }
}

function chooseFile(event: Event) {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function upload() {
  if (!selectedFile.value) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const form = new FormData()
    form.append('image', selectedFile.value)
    submission.value = await apiPostForm<DeckSubmission>(
      `/tournaments/${props.tournamentId}/deck-submission`, form, props.token,
    )
    selectedFile.value = null
    message.value = '卡组截图已提交，等待管理员审核。'
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '卡组截图上传失败'
  } finally { busy.value = false }
}

onMounted(load)
</script>

<template>
  <section v-if="eligible && submission" class="info-section deck-upload-panel">
    <p class="section-kicker">TOP 4 DECK</p>
    <div class="section-title-row"><div><h2>四强卡组截图</h2><p>你是本届赛事{{ deckPlacementText(submission.placement) }}，请上传本届赛事使用的 Master Duel 卡组截图。</p></div><span :class="['status-badge', `deck-${submission.status.toLowerCase()}`]">{{ deckStatusText[submission.status] }}</span></div>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />
    <img v-if="submission.image_url" class="deck-preview" :src="submission.image_url" alt="已提交的卡组截图" />
    <p v-if="submission.review_note" class="review-note">退回原因：{{ submission.review_note }}</p>
    <div v-if="submission.status !== 'APPROVED'" class="deck-upload-actions">
      <label class="file-control"><span>{{ submission.image_url ? '选择新的截图' : '选择卡组截图' }}</span><input type="file" accept="image/jpeg,image/png,image/webp" @change="chooseFile" /></label>
      <button class="button primary" type="button" :disabled="busy || !selectedFile" @click="upload">{{ submission.image_url ? '重新上传' : '上传截图' }}</button>
    </div>
    <p v-else class="form-hint">截图已审核通过并锁定，将用于本届赛事周报。</p>
  </section>
  <section v-else-if="eligible === false" class="info-section deck-upload-panel">
    <p class="section-kicker">DECK</p>
    <h2>卡组截图</h2>
    <p class="empty-state compact">卡组上传仅向本届赛事最终四强开放。</p>
  </section>
  <section v-else-if="error" class="info-section deck-upload-panel">
    <p class="section-kicker">DECK</p>
    <h2>卡组截图</h2>
    <FormMessage :message="error" />
  </section>
</template>
