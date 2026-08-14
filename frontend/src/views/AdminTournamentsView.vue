<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useAuthStore } from '@/stores/auth'
import type { BanlistVersion, ListResponse } from '@/types/content'
import type { Tournament, TournamentListResponse } from '@/types/tournament'
import { tournamentStatusText } from '@/types/tournament'

const authStore = useAuthStore()
const tournaments = ref<Tournament[]>([])
const banlists = ref<BanlistVersion[]>([])
const error = ref('')
const message = ref('')
const busy = ref(false)
const isCreateOpen = ref(false)
const pendingDraftId = ref('')
const pendingDraftName = ref('')
const tournamentNameInput = ref<HTMLInputElement | null>(null)
const form = reactive({
  name: '', description: '', planned_start_at: '', max_players: 32, swiss_rounds: 5,
  playoff_size: 8, banlist_version_id: '',
})

function resetForm() {
  form.name = ''
  form.description = ''
  form.planned_start_at = ''
  form.max_players = 32
  form.swiss_rounds = 5
  form.playoff_size = 8
  form.banlist_version_id = banlists.value[0]?.id ?? ''
}

async function openCreatePanel() {
  error.value = ''
  message.value = ''
  isCreateOpen.value = true
  await nextTick()
  tournamentNameInput.value?.focus()
}

function cancelCreate() {
  isCreateOpen.value = false
  if (!pendingDraftId.value) resetForm()
  error.value = ''
}

async function load() {
  const [tournamentData, banlistData] = await Promise.all([
    apiGet<TournamentListResponse>('/admin/tournaments?limit=100', undefined, authStore.token),
    apiGet<ListResponse<BanlistVersion>>('/banlists?limit=100'),
  ])
  tournaments.value = tournamentData.items.filter((item) => item.status !== 'DRAFT')
  banlists.value = banlistData.items
  if (!form.banlist_version_id && banlists.value[0]) form.banlist_version_id = banlists.value[0].id
}

async function createTournament() {
  busy.value = true
  error.value = ''
  message.value = ''

  if (!pendingDraftId.value) {
    try {
      const item = await apiPost<Tournament>('/admin/tournaments', {
        ...form,
        planned_start_at: new Date(form.planned_start_at).toISOString(),
      }, authStore.token)
      pendingDraftId.value = item.id
      pendingDraftName.value = item.name
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '创建赛事失败'
      busy.value = false
      return
    }
  }

  try {
    await apiPost<Tournament>(`/admin/tournaments/${pendingDraftId.value}/publish`, {}, authStore.token)
  } catch (caught) {
    const reason = caught instanceof Error ? caught.message : '发布赛事失败'
    error.value = `“${pendingDraftName.value}”创建成功但尚未发布：${reason}。请点击“重新发布”。`
    busy.value = false
    return
  }

  const publishedName = pendingDraftName.value
  pendingDraftId.value = ''
  pendingDraftName.value = ''
  message.value = `“${publishedName}”已创建并开放报名。`
  isCreateOpen.value = false
  resetForm()
  await load().catch((caught) => {
    error.value = caught instanceof Error ? `赛事已创建，但列表刷新失败：${caught.message}` : '赛事已创建，但列表刷新失败'
  })
  busy.value = false
}

function formatDate(value: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '未设置'
}

onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '赛事管理加载失败' }))
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading split-heading">
      <div><p class="section-kicker">TOURNAMENT MANAGEMENT</p><h1>赛事管理</h1><p>创建并发布赛事，进入报名审核与赛事运营。</p></div>
      <button class="button primary" type="button" aria-controls="create-tournament-form" :aria-expanded="isCreateOpen" :disabled="isCreateOpen" @click="openCreatePanel">创建赛事</button>
    </header>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />
    <form v-if="isCreateOpen" id="create-tournament-form" class="content-form tournament-form" @submit.prevent="createTournament">
      <div class="tournament-form-heading">
        <div><h2>创建新赛事</h2><p>填写完整信息后，赛事将立即发布并开放报名。</p></div>
        <button class="button secondary small" type="button" :disabled="busy" @click="cancelCreate">取消</button>
      </div>
      <label><span>赛事名称</span><input ref="tournamentNameInput" v-model.trim="form.name" maxlength="120" required /></label>
      <label><span>赛事说明</span><textarea v-model.trim="form.description" rows="4" maxlength="10000" /></label>
      <label><span>预计比赛开始时间</span><input v-model="form.planned_start_at" type="datetime-local" required /></label>
      <div class="form-field-grid">
        <label><span>最大参赛人数</span><input v-model.number="form.max_players" type="number" min="2" max="1024" required /></label>
        <label><span>瑞士轮轮数</span><input v-model.number="form.swiss_rounds" type="number" min="1" max="20" required /></label>
        <label><span>Top N</span><select v-model.number="form.playoff_size"><option v-for="size in [2,4,8,16,32,64]" :key="size" :value="size">Top {{ size }}</option></select></label>
      </div>
      <label><span>禁卡表版本</span><select v-model="form.banlist_version_id" required><option disabled value="">请选择已发布版本</option><option v-for="item in banlists" :key="item.id" :value="item.id">{{ item.version }} · {{ item.title }}</option></select></label>
      <p v-if="!banlists.length" class="form-hint">请先发布至少一个禁卡表版本。</p>
      <div class="form-actions">
        <button class="button primary" type="submit" :disabled="busy || !banlists.length">{{ busy ? '正在发布…' : pendingDraftId ? '重新发布' : '创建并发布' }}</button>
      </div>
    </form>
    <section class="admin-tournament-list">
      <h2>全部赛事</h2>
      <p v-if="!tournaments.length" class="empty-state">尚未创建赛事。</p>
      <article v-for="item in tournaments" :key="item.id" class="admin-tournament-row">
        <div><span :class="['status-badge', `status-${item.status.toLowerCase()}`]">{{ tournamentStatusText[item.status] }}</span><strong>{{ item.name }}</strong><small>{{ formatDate(item.planned_start_at) }}</small></div>
        <div class="row-actions">
          <RouterLink class="button secondary small" :to="`/admin/tournaments/${item.id}/settings`">管理</RouterLink>
        </div>
      </article>
    </section>
  </div>
</template>
