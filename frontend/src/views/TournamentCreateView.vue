<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { apiGet, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { BanlistVersion, ListResponse } from '@/types/content'
import type { Tournament } from '@/types/tournament'
import { combineLocalDateAndTime } from '@/utils/dateTime'

const authStore = useAuthStore()
const router = useRouter()
const banlists = ref<BanlistVersion[]>([])
const published = ref<Tournament | null>(null)
const busy = ref(false)
const error = ref('')
const copyMessage = ref('')
const form = reactive({
  name: '', description: '', planned_start_date: '', planned_start_time: '', max_players: 32,
  swiss_rounds: 5, playoff_size: 8, banlist_version_id: '',
})

async function publishTournament() {
  busy.value = true
  error.value = ''
  try {
    const { planned_start_date, planned_start_time, ...payload } = form
    published.value = await apiPost<Tournament>('/tournaments', {
      ...payload,
      planned_start_at: combineLocalDateAndTime(planned_start_date, planned_start_time),
    }, authStore.token)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '比赛发布失败'
  } finally {
    busy.value = false
  }
}

async function copyCode() {
  if (!published.value?.code) return
  await navigator.clipboard.writeText(published.value.code)
  copyMessage.value = '比赛码已复制'
}

onMounted(async () => {
  try {
    banlists.value = (await apiGet<ListResponse<BanlistVersion>>('/banlists?limit=100')).items
    form.banlist_version_id = banlists.value[0]?.id ?? ''
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '禁卡表加载失败'
  }
})
</script>

<template>
  <div class="page-shell tournament-create-page">
    <header class="page-heading">
      <p class="section-kicker">PUBLISH TOURNAMENT</p>
      <h1>发布比赛</h1>
      <p>填写完整信息后立即开放报名，发布成功会生成专属比赛码。</p>
    </header>

    <section v-if="published" class="publish-success" aria-live="polite">
      <p class="section-kicker">PUBLISHED</p>
      <h2>比赛已发布</h2>
      <p>把比赛码发给参赛者，他们可以在赛事中心直接查找。</p>
      <div class="published-code"><span>比赛码</span><strong>{{ published.code }}</strong><button class="button secondary small" type="button" @click="copyCode">复制</button></div>
      <p v-if="copyMessage" class="form-hint">{{ copyMessage }}</p>
      <div class="form-actions">
        <button class="button primary" type="button" @click="router.push(`/tournaments/${published.id}/manage/settings`)">管理比赛</button>
        <button class="button secondary" type="button" @click="router.push(`/tournaments/${published.id}`)">查看赛事页面</button>
      </div>
    </section>

    <form v-else class="content-form tournament-form tournament-publish-form" @submit.prevent="publishTournament">
      <div class="tournament-form-heading"><div><h2>比赛信息</h2><p>所有带星号的信息会直接展示给参赛者。</p></div></div>
      <FormMessage v-if="error" :message="error" />
      <label><span>赛事名称 *</span><input v-model.trim="form.name" maxlength="120" required autofocus /></label>
      <label><span>赛事说明</span><textarea v-model.trim="form.description" rows="6" maxlength="10000" placeholder="说明比赛安排、报名要求或其他注意事项" /></label>
      <div class="date-time-field-grid">
        <label><span>开赛日期 *</span><input v-model="form.planned_start_date" type="date" required /></label>
        <label><span>开赛时间 *</span><input v-model="form.planned_start_time" type="time" required /></label>
      </div>
      <div class="form-field-grid">
        <label><span>最大参赛人数 *</span><input v-model.number="form.max_players" type="number" min="2" max="1024" required /></label>
        <label><span>瑞士轮轮数 *</span><input v-model.number="form.swiss_rounds" type="number" min="1" max="20" required /></label>
        <label><span>淘汰赛晋级 *</span><select v-model.number="form.playoff_size"><option v-for="size in [2,4,8,16,32,64]" :key="size" :value="size">Top {{ size }}</option></select></label>
      </div>
      <label><span>禁卡表版本 *</span><select v-model="form.banlist_version_id" required><option disabled value="">请选择已发布版本</option><option v-for="item in banlists" :key="item.id" :value="item.id">{{ item.version }} · {{ item.title }}</option></select></label>
      <p v-if="!banlists.length" class="form-hint">当前没有可用的已发布禁卡表，请联系平台管理员。</p>
      <div class="form-actions"><RouterLink class="button secondary" to="/tournaments">取消</RouterLink><button class="button primary" type="submit" :disabled="busy || !banlists.length">{{ busy ? '正在发布…' : '发布比赛' }}</button></div>
    </form>
  </div>
</template>
