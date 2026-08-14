<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { apiGet, apiPatch, apiPost } from '@/api/client'
import ConfirmFormDialog from '@/components/ConfirmFormDialog.vue'
import FormMessage from '@/components/FormMessage.vue'
import WeeklyReportContent from '@/components/WeeklyReportContent.vue'
import { useAuthStore } from '@/stores/auth'
import type { BanlistVersion, ListResponse } from '@/types/content'
import type { DeckSubmission, DeckSubmissionList, WeeklyReport } from '@/types/report'
import { deckStatusText } from '@/types/report'
import type { AuditLogListResponse, MessageSendResponse } from '@/types/message'
import type {
  Participant, PlayoffMatch, PlayoffOverview, Registration, RegistrationBulkApproveResponse, RegistrationListResponse, SwissMatch, SwissOverview, SwissRound, Tournament,
} from '@/types/tournament'
import { matchStatusText, registrationStatusText, swissRoundStatusText, tournamentStatusText } from '@/types/tournament'

type PendingPlayoffForfeit = {
  match: PlayoffMatch
  loserId: string
  loserNickname: string
  winnerNickname: string
  reason: string
}

const route = useRoute()
const authStore = useAuthStore()
const tournament = ref<Tournament | null>(null)
const registrations = ref<Registration[]>([])
const banlists = ref<BanlistVersion[]>([])
const swissRounds = ref<SwissRound[]>([])
const swissOverview = ref<SwissOverview | null>(null)
const participants = ref<Participant[]>([])
const playoff = ref<PlayoffOverview | null>(null)
const forfeitReason = ref('选手无法继续参赛')
const pendingPlayoffForfeit = ref<PendingPlayoffForfeit | null>(null)
const deckSubmissions = ref<DeckSubmissionList | null>(null)
const weeklyReport = ref<WeeklyReport | null>(null)
const auditLogs = ref<AuditLogListResponse | null>(null)
const noticeForm = reactive({ title: '', body: '' })
const deckReturnReason = ref('截图信息不完整，请重新上传')
const matchFilter = ref<'ALL' | 'WAITING' | 'CONFLICT' | 'COMPLETED'>('ALL')
const swapFirst = ref('')
const swapSecond = ref('')
const error = ref('')
const message = ref('')
const busy = ref(false)
const bulkApprovalOpen = ref(false)
const startTournamentOpen = ref(false)
const publishSwissRoundOpen = ref(false)
const tournamentId = computed(() => String(route.params.id))
const section = computed(() => String(route.params.section || 'settings'))
const coreLocked = computed(() => tournament.value ? ['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.value.status) : false)
const latestRound = computed<SwissRound | null>(() => swissRounds.value[swissRounds.value.length - 1] ?? null)
const filteredMatches = computed<SwissMatch[]>(() => {
  const matches = latestRound.value?.matches ?? []
  if (latestRound.value?.status === 'DRAFT') return matches
  return matchFilter.value === 'ALL' ? matches : matches.filter((item) => item.status === matchFilter.value)
})
const draftParticipantIds = computed<string[]>(() => {
  if (latestRound.value?.status !== 'DRAFT') return []
  return latestRound.value.matches.flatMap((item: SwissMatch) =>
    [item.player_a_id, item.player_b_id].filter((id): id is string => Boolean(id)),
  )
})
const withdrawalOpen = computed(() => !latestRound.value || ['DRAFT', 'COMPLETED'].includes(latestRound.value.status))
const latestPlayoffRound = computed(() => playoff.value?.rounds[playoff.value.rounds.length - 1] ?? null)
const swissRecords = computed(() => new Map(
  (swissOverview.value?.rankings ?? []).map((item) => [item.participant_id, `${item.wins}-${item.losses}`]),
))
const form = reactive({ name: '', description: '', planned_start_at: '', max_players: 32, swiss_rounds: 5, playoff_size: 8, banlist_version_id: '' })

const swissRecord = (participantId: string) => swissRecords.value.get(participantId) ?? '0-0'

function toLocalInput(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function syncForm(item: Tournament) {
  form.name = item.name
  form.description = item.description
  form.planned_start_at = toLocalInput(item.planned_start_at)
  form.max_players = item.max_players ?? 32
  form.swiss_rounds = item.swiss_rounds ?? 5
  form.playoff_size = item.playoff_size ?? 8
  form.banlist_version_id = item.banlist_version_id ?? ''
}

async function load() {
  const [item, banlistData] = await Promise.all([
    apiGet<Tournament>(`/admin/tournaments/${tournamentId.value}`, undefined, authStore.token),
    apiGet<ListResponse<BanlistVersion>>('/banlists?limit=100'),
  ])
  tournament.value = item
  banlists.value = banlistData.items
  syncForm(item)
  if (section.value === 'registrations') await loadRegistrations()
  if (section.value === 'matches' && item.status === 'SWISS') await loadSwiss()
  if (section.value === 'playoffs' && ['SWISS', 'ELIMINATION', 'ENDED'].includes(item.status)) await loadPlayoffs()
  if (section.value === 'decks-report' && item.status === 'ENDED') await loadPhase5()
  if (section.value === 'audit') await loadAuditLogs()
}

async function loadAuditLogs() {
  auditLogs.value = await apiGet<AuditLogListResponse>(
    `/tournaments/${tournamentId.value}/audit-logs?limit=100`, undefined, authStore.token,
  )
}

async function sendTournamentNotice() {
  if (!window.confirm('确认向本届全部正式参赛玩家发送这条赛事通知？')) return
  busy.value = true
  error.value = ''
  try {
    const result = await apiPost<MessageSendResponse>(
      `/admin/tournaments/${tournamentId.value}/messages`,
      { ...noticeForm, request_id: crypto.randomUUID() },
      authStore.token,
    )
    message.value = `赛事通知已发送给 ${result.sent_count} 名正式参赛玩家。`
    noticeForm.title = ''
    noticeForm.body = ''
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事通知发送失败'
  } finally { busy.value = false }
}

const formatAuditTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

async function loadRegistrations() {
  registrations.value = (await apiGet<RegistrationListResponse>(
    `/admin/tournaments/${tournamentId.value}/registrations`, undefined, authStore.token,
  )).items
}

async function loadSwiss() {
  const [rounds, overview, participantItems] = await Promise.all([
    apiGet<SwissRound[]>(`/admin/tournaments/${tournamentId.value}/swiss/rounds`, undefined, authStore.token),
    apiGet<SwissOverview>(`/tournaments/${tournamentId.value}/swiss`),
    apiGet<Participant[]>(`/admin/tournaments/${tournamentId.value}/participants`, undefined, authStore.token),
  ])
  swissRounds.value = rounds
  swissOverview.value = overview
  participants.value = participantItems
  swapFirst.value = ''
  swapSecond.value = ''
}

async function loadPlayoffs() {
  playoff.value = await apiGet<PlayoffOverview>(
    `/admin/tournaments/${tournamentId.value}/playoffs`, undefined, authStore.token,
  )
}

async function loadPhase5() {
  deckSubmissions.value = await apiGet<DeckSubmissionList>(
    `/admin/tournaments/${tournamentId.value}/deck-submissions`, undefined, authStore.token,
  )
  weeklyReport.value = await apiGet<WeeklyReport>(
    `/admin/tournaments/${tournamentId.value}/report`, undefined, authStore.token,
  ).catch(() => null)
}

async function saveSettings() {
  busy.value = true
  error.value = ''
  try {
    const payload = {
      ...form,
      planned_start_at: new Date(form.planned_start_at).toISOString(),
    }
    tournament.value = await apiPatch<Tournament>(`/admin/tournaments/${tournamentId.value}`, payload, authStore.token)
    message.value = '赛事设置已保存。'
    syncForm(tournament.value)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '保存失败'
  } finally { busy.value = false }
}

async function publishTournament() {
  await lifecycleAction('publish', '赛事已发布并立即开放报名。')
}

function requestTournamentStart() {
  error.value = ''
  startTournamentOpen.value = true
}

function cancelTournamentStart() {
  if (!busy.value) startTournamentOpen.value = false
}

async function startTournament() {
  const succeeded = await lifecycleAction('start', '赛事已开始，正式参赛名单快照已生成。')
  if (succeeded) startTournamentOpen.value = false
}

async function lifecycleAction(action: 'publish' | 'start', successMessage: string) {
  busy.value = true
  error.value = ''
  try {
    tournament.value = await apiPost<Tournament>(`/admin/tournaments/${tournamentId.value}/${action}`, {}, authStore.token)
    message.value = successMessage
    syncForm(tournament.value)
    return true
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '操作失败'
    return false
  } finally { busy.value = false }
}

async function review(item: Registration, action: 'approve' | 'reject' | 'cancel' | 'restore') {
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/tournaments/${tournamentId.value}/registrations/${item.id}/${action}`, {}, authStore.token)
    message.value = '报名状态已更新。'
    await Promise.all([loadRegistrations(), loadTournamentSummary()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '审核操作失败'
  } finally { busy.value = false }
}

function requestPendingApproval() {
  if (!tournament.value?.pending_count) return
  error.value = ''
  bulkApprovalOpen.value = true
}

function cancelPendingApproval() {
  if (!busy.value) bulkApprovalOpen.value = false
}

async function approvePendingRegistrations() {
  const pendingCount = tournament.value?.pending_count ?? 0
  if (!pendingCount) {
    bulkApprovalOpen.value = false
    return
  }
  busy.value = true
  error.value = ''
  try {
    const result = await apiPost<RegistrationBulkApproveResponse>(
      `/admin/tournaments/${tournamentId.value}/registrations/approve-pending`, {}, authStore.token,
    )
    message.value = `已批量通过 ${result.approved_count} 名待审核选手。`
    await Promise.all([loadRegistrations(), loadTournamentSummary()])
    bulkApprovalOpen.value = false
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '批量审核失败'
  } finally { busy.value = false }
}

async function loadTournamentSummary() {
  tournament.value = await apiGet<Tournament>(`/admin/tournaments/${tournamentId.value}`, undefined, authStore.token)
}

async function swissAction(action: 'generate' | 'regenerate') {
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/tournaments/${tournamentId.value}/swiss/rounds/${action}`, {}, authStore.token)
    message.value = action === 'generate' ? '下一轮对阵预览已生成。' : '对阵预览已重新生成。'
    await loadSwiss()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '生成对阵失败'
  } finally { busy.value = false }
}

function requestSwissRoundPublish() {
  if (!latestRound.value || latestRound.value.status !== 'DRAFT') return
  error.value = ''
  publishSwissRoundOpen.value = true
}

function cancelSwissRoundPublish() {
  if (!busy.value) publishSwissRoundOpen.value = false
}

async function publishSwissRound() {
  if (!latestRound.value || latestRound.value.status !== 'DRAFT') {
    publishSwissRoundOpen.value = false
    return
  }
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/tournaments/${tournamentId.value}/swiss/rounds/${latestRound.value.id}/publish`, {}, authStore.token)
    message.value = `第 ${latestRound.value.round_no} 轮已正式发布。`
    await loadSwiss()
    publishSwissRoundOpen.value = false
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '轮次发布失败'
  } finally { busy.value = false }
}

async function swapPlayers() {
  if (!latestRound.value || !swapFirst.value || !swapSecond.value) return
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/tournaments/${tournamentId.value}/swiss/rounds/${latestRound.value.id}/swap`, {
      first_participant_id: swapFirst.value,
      second_participant_id: swapSecond.value,
    }, authStore.token)
    message.value = '两名选手的位置已交换。'
    await loadSwiss()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '交换选手失败'
  } finally { busy.value = false }
}

async function resolveMatch(match: SwissMatch, winnerId: string) {
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/matches/${match.id}/resolve`, { winner_id: winnerId }, authStore.token)
    message.value = '赛果已由赛事主办方确认。'
    await loadSwiss()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛果裁定失败'
  } finally { busy.value = false }
}

async function withdraw(participant: Participant) {
  if (!window.confirm(`确认将“${participant.nickname_snapshot}”标记为退赛？历史赛果会保留。`)) return
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/tournaments/${tournamentId.value}/participants/${participant.id}/withdraw`, {}, authStore.token)
    message.value = '选手已退赛；若存在未发布预览，系统已自动作废。'
    await loadSwiss()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '退赛操作失败'
  } finally { busy.value = false }
}

async function generatePlayoffStage() {
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/tournaments/${tournamentId.value}/playoffs/generate`, {}, authStore.token)
    message.value = '淘汰阶段固定种子签表预览已生成。'
    await loadPlayoffs()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '淘汰阶段生成失败'
  } finally { busy.value = false }
}

async function publishPlayoffStage() {
  if (!latestPlayoffRound.value || !window.confirm(`发布${latestPlayoffRound.value.name}后签表不可修改，是否继续？`)) return
  busy.value = true
  error.value = ''
  try {
    await apiPost(
      `/admin/tournaments/${tournamentId.value}/playoffs/rounds/${latestPlayoffRound.value.id}/publish`, {}, authStore.token,
    )
    message.value = `${latestPlayoffRound.value.name}已正式发布。`
    await Promise.all([loadPlayoffs(), loadTournamentSummary()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '淘汰阶段发布失败'
  } finally { busy.value = false }
}

async function endTournament() {
  if (!window.confirm('确认结束赛事？结束后全部赛果将永久锁定，并向最终四强开放卡组截图上传。')) return
  busy.value = true
  error.value = ''
  try {
    tournament.value = await apiPost<Tournament>(
      `/admin/tournaments/${tournamentId.value}/end`, {}, authStore.token,
    )
    message.value = '赛事已结束，全部赛果已永久锁定。'
    await Promise.all([loadPlayoffs(), loadPhase5()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '结束赛事失败'
  } finally { busy.value = false }
}

async function reviewDeck(item: DeckSubmission, action: 'approve' | 'return') {
  if (action === 'return' && !deckReturnReason.value.trim()) {
    error.value = '退回截图必须填写原因。'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/deck-submissions/${item.id}/${action}`, action === 'return'
      ? { reason: deckReturnReason.value.trim() }
      : {}, authStore.token)
    message.value = action === 'approve' ? '卡组截图已审核通过并锁定。' : '截图已退回，等待选手重新上传。'
    await loadPhase5()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '卡组截图审核失败'
  } finally { busy.value = false }
}

async function generateWeeklyReport() {
  busy.value = true
  error.value = ''
  try {
    weeklyReport.value = await apiPost<WeeklyReport>(
      `/admin/tournaments/${tournamentId.value}/reports/generate`, {}, authStore.token,
    )
    message.value = '周报草稿已按赛事结构化数据生成，请预览后发布。'
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '周报生成失败'
  } finally { busy.value = false }
}

async function publishWeeklyReport() {
  if (!weeklyReport.value || !window.confirm('确认发布周报？发布后不可撤回、修改或替换四强截图。')) return
  busy.value = true
  error.value = ''
  try {
    weeklyReport.value = await apiPost<WeeklyReport>(
      `/admin/reports/${weeklyReport.value.id}/publish`, {}, authStore.token,
    )
    message.value = '周报已发布并永久锁定。'
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '周报发布失败'
  } finally { busy.value = false }
}

function requestPlayoffForfeit(match: PlayoffMatch, loserId: string) {
  const reason = forfeitReason.value.trim()
  if (!reason) {
    error.value = '主办方判负必须填写原因。'
    return
  }
  const loserNickname = loserId === match.player_a_id ? match.player_a_nickname : match.player_b_nickname
  const winnerNickname = loserId === match.player_a_id ? match.player_b_nickname : match.player_a_nickname
  error.value = ''
  pendingPlayoffForfeit.value = { match, loserId, loserNickname, winnerNickname, reason }
}

function cancelPlayoffForfeit() {
  pendingPlayoffForfeit.value = null
}

async function confirmPlayoffForfeit() {
  const pending = pendingPlayoffForfeit.value
  if (!pending) return
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/playoffs/matches/${pending.match.id}/forfeit`, {
      loser_id: pending.loserId,
      reason: pending.reason,
    }, authStore.token)
    pendingPlayoffForfeit.value = null
    message.value = '主办方判负已生效并写入审计记录。'
    await loadPlayoffs()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '主办方判负失败'
  } finally { busy.value = false }
}

watch(section, async (value) => {
  if (value === 'registrations') await loadRegistrations()
  if (value === 'matches' && tournament.value?.status === 'SWISS') await loadSwiss()
  if (value === 'playoffs' && tournament.value && ['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.value.status)) await loadPlayoffs()
  if (value === 'decks-report' && tournament.value?.status === 'ENDED') await loadPhase5()
  if (value === 'audit') await loadAuditLogs()
})
onMounted(() => load().catch((caught) => { error.value = caught instanceof Error ? caught.message : '赛事加载失败' }))
</script>

<template>
  <div class="page-shell admin-page">
    <header v-if="tournament" class="page-heading split-heading">
      <div><p class="section-kicker">TOURNAMENT OPERATION</p><h1>{{ tournament.name }}</h1><p>状态：{{ tournamentStatusText[tournament.status] }} · 已通过 {{ tournament.approved_count }} 人 · 待审核 {{ tournament.pending_count }} 人</p></div>
      <RouterLink class="button secondary" :to="`/tournaments/${tournament.id}`">查看公开页面</RouterLink>
    </header>
    <nav class="admin-subnav" aria-label="赛事管理导航">
      <RouterLink :to="`/tournaments/${tournamentId}/manage/settings`">赛事设置</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/registrations`">报名管理</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/matches`">对局与排名</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/playoffs`">淘汰赛</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/decks-report`">卡组与周报</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/notifications`">赛事通知</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/audit`">操作日志</RouterLink>
    </nav>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />
    <ConfirmFormDialog
      v-if="bulkApprovalOpen && tournament"
      title="批量通过报名"
      :description="`将一次通过全部 ${tournament.pending_count} 名待审核选手，并向他们发送审核通过通知。`"
      confirm-text="确认批量通过"
      :busy="busy"
      :error="error"
      @cancel="cancelPendingApproval"
      @confirm="approvePendingRegistrations"
    />
    <ConfirmFormDialog
      v-if="startTournamentOpen && tournament"
      title="开始赛事"
      description="开始后将立即关闭报名、锁定核心配置，并根据已通过报名生成正式参赛名单。"
      confirm-text="确认开始赛事"
      :busy="busy"
      :error="error"
      @cancel="cancelTournamentStart"
      @confirm="startTournament"
    />
    <ConfirmFormDialog
      v-if="publishSwissRoundOpen && latestRound"
      :title="`正式发布第 ${latestRound.round_no} 轮`"
      description="发布后本轮对阵不可修改，选手将可以查看对手并提交赛果。"
      confirm-text="确认正式发布"
      :busy="busy"
      :error="error"
      @cancel="cancelSwissRoundPublish"
      @confirm="publishSwissRound"
    />

    <form v-if="tournament && section === 'settings'" class="content-form tournament-settings" @submit.prevent="saveSettings">
      <div class="settings-heading"><div><h2>赛事设置</h2><p v-if="coreLocked" class="form-hint">赛事已经开始，容量、轮数、Top N 和禁卡表版本已锁定。</p></div><span :class="['status-badge', `status-${tournament.status.toLowerCase()}`]">{{ tournamentStatusText[tournament.status] }}</span></div>
      <label><span>赛事名称</span><input v-model.trim="form.name" required /></label>
      <label><span>赛事说明</span><textarea v-model.trim="form.description" rows="5" /></label>
      <label><span>预计比赛开始时间</span><input v-model="form.planned_start_at" type="datetime-local" required /></label>
      <div class="form-field-grid">
        <label><span>最大参赛人数</span><input v-model.number="form.max_players" type="number" min="2" :disabled="coreLocked" /></label>
        <label><span>瑞士轮轮数</span><input v-model.number="form.swiss_rounds" type="number" min="1" :disabled="coreLocked" /></label>
        <label><span>Top N</span><select v-model.number="form.playoff_size" :disabled="coreLocked"><option v-for="size in [2,4,8,16,32,64]" :key="size" :value="size">Top {{ size }}</option></select></label>
      </div>
      <label><span>禁卡表版本</span><select v-model="form.banlist_version_id" :disabled="coreLocked"><option v-for="item in banlists" :key="item.id" :value="item.id">{{ item.version }} · {{ item.title }}</option></select></label>
      <div class="form-actions">
        <button class="button secondary" type="submit" :disabled="busy">保存设置</button>
        <button v-if="tournament.status === 'DRAFT'" class="button primary" type="button" :disabled="busy" @click="publishTournament">发布并开放报名</button>
        <button v-if="tournament.status === 'REGISTRATION'" class="button primary" type="button" :disabled="busy" @click="requestTournamentStart">开始赛事</button>
      </div>
    </form>

    <section v-if="tournament && section === 'registrations'" class="registration-management">
      <div class="settings-heading">
        <div><h2>报名管理</h2><p>只展示昵称、状态与必要操作；审核通过人数不会超过 {{ tournament.max_players }} 人。</p></div>
        <div class="registration-heading-actions">
          <button class="button primary small" type="button" :disabled="busy || tournament.pending_count === 0" @click="requestPendingApproval">批量通过</button>
          <span>待审核 {{ tournament.pending_count }}</span>
        </div>
      </div>
      <p v-if="!registrations.length" class="empty-state">暂无报名记录。</p>
      <article v-for="item in registrations" :key="item.id" class="registration-row">
        <strong>{{ item.nickname }}</strong>
        <span :class="['status-badge', `registration-${item.status.toLowerCase()}`]">{{ registrationStatusText[item.status] }}</span>
        <div class="row-actions">
          <template v-if="item.status === 'PENDING'"><button type="button" @click="review(item, 'approve')">通过</button><button type="button" @click="review(item, 'reject')">拒绝</button></template>
          <button v-if="item.status === 'APPROVED'" type="button" @click="review(item, 'cancel')">取消</button>
          <button v-if="['REJECTED','CANCELED'].includes(item.status)" type="button" @click="review(item, 'restore')">恢复为已通过</button>
        </div>
      </article>
    </section>

    <section v-if="tournament && section === 'matches'" class="swiss-admin">
      <div v-if="tournament.status !== 'SWISS'" class="empty-state">赛事进入瑞士轮后开放对局管理。</div>
      <template v-else>
        <div class="swiss-operation-bar">
          <div><h2>瑞士轮对局</h2><p>生成只是预览；正式发布后对阵不可修改，并锁定上一轮赛果。</p></div>
          <div class="form-actions">
            <button v-if="!latestRound || latestRound.status === 'COMPLETED'" class="button primary" type="button" :disabled="busy || (swissOverview?.completed_rounds ?? 0) >= (tournament.swiss_rounds ?? 0)" @click="swissAction('generate')">生成下一轮</button>
            <template v-if="latestRound?.status === 'DRAFT'">
              <button class="button secondary" type="button" :disabled="busy" @click="swissAction('regenerate')">重新生成</button>
              <button class="button primary" type="button" :disabled="busy" @click="requestSwissRoundPublish">正式发布</button>
            </template>
          </div>
        </div>

        <div v-if="latestRound" class="round-admin-heading">
          <div><strong>第 {{ latestRound.round_no }} 轮</strong><span :class="['status-badge', `round-${latestRound.status.toLowerCase()}`]">{{ swissRoundStatusText[latestRound.status] }}</span></div>
          <label v-if="latestRound.status !== 'DRAFT'">筛选
            <select v-model="matchFilter"><option value="ALL">全部</option><option value="WAITING">未完成</option><option value="CONFLICT">赛果冲突</option><option value="COMPLETED">已完成</option></select>
          </label>
        </div>

        <div v-if="latestRound?.status === 'DRAFT'" class="swap-panel">
          <strong>交换选手 / 更换 BYE</strong>
          <select v-model="swapFirst"><option value="">选择第一名选手</option><option v-for="item in draftParticipantIds" :key="item" :value="item">{{ participants.find((participant) => participant.id === item)?.nickname_snapshot }}</option></select>
          <select v-model="swapSecond"><option value="">选择第二名选手</option><option v-for="item in draftParticipantIds" :key="item" :value="item">{{ participants.find((participant) => participant.id === item)?.nickname_snapshot }}</option></select>
          <button class="button secondary small" type="button" :disabled="busy || !swapFirst || !swapSecond || swapFirst === swapSecond" @click="swapPlayers">交换位置</button>
        </div>

        <div v-if="latestRound" class="admin-match-list">
          <article v-for="match in filteredMatches" :key="match.id" :class="['admin-match-row', { 'admin-match-row-preview': latestRound.status === 'DRAFT' }]">
            <span class="match-table-no">第 {{ match.table_no }} 桌</span>
            <div class="admin-match-players">
              <span class="admin-match-player"><strong>{{ match.player_a_nickname }}</strong><em v-if="latestRound.status === 'DRAFT'">（{{ swissRecord(match.player_a_id) }}）</em></span>
              <span class="admin-match-player"><strong>{{ match.player_b_nickname || '轮空' }}</strong><em v-if="latestRound.status === 'DRAFT' && match.player_b_id">（{{ swissRecord(match.player_b_id) }}）</em></span>
              <small v-if="match.warnings.length">{{ match.warnings.join(' · ') }}</small>
            </div>
            <div v-if="latestRound.status !== 'DRAFT' && match.player_b_id" class="submission-state"><span>A：{{ match.player_a_result === 'WIN' ? '胜' : match.player_a_result === 'LOSS' ? '负' : '未提交' }}</span><span>B：{{ match.player_b_result === 'WIN' ? '胜' : match.player_b_result === 'LOSS' ? '负' : '未提交' }}</span></div>
            <span v-else-if="latestRound.status !== 'DRAFT'" class="bye-auto-win">轮空自动获胜</span>
            <span v-if="latestRound.status !== 'DRAFT'" :class="['status-badge', `match-${match.status.toLowerCase()}`]">{{ matchStatusText[match.status] }}</span>
            <div v-if="latestRound.status !== 'DRAFT' && match.player_b_id && !match.result_locked" class="row-actions"><button type="button" @click="resolveMatch(match, match.player_a_id)">判 A 胜</button><button type="button" @click="resolveMatch(match, match.player_b_id)">判 B 胜</button></div>
          </article>
          <p v-if="!filteredMatches.length" class="empty-state compact">该筛选下没有对局。</p>
        </div>

        <div class="swiss-admin-grid">
          <section><div class="ranking-heading"><h2>正式排名</h2><span>第 {{ swissOverview?.ranking_round_no ?? 0 }} 轮快照</span></div><div class="ranking-table-wrap"><table class="ranking-table"><thead><tr><th>排名</th><th>选手</th><th>胜负</th><th>OMW</th><th>败局小分</th></tr></thead><tbody><tr v-for="item in swissOverview?.rankings" :key="item.participant_id"><td>{{ item.rank }}</td><td>{{ item.nickname }}</td><td>{{ item.wins }}-{{ item.losses }}</td><td>{{ (item.omw * 100).toFixed(2) }}%</td><td>{{ item.loss_round_score }}</td></tr><tr v-if="!swissOverview?.rankings.length"><td colspan="5">尚无正式排名。</td></tr></tbody></table></div></section>
          <section class="withdrawal-panel"><div><h2>退赛管理</h2><p>仅轮次结束且下一轮未发布时允许；未发布预览会被作废。</p></div><article v-for="item in participants" :key="item.id"><span><strong>{{ item.nickname_snapshot }}</strong><small>BYE {{ item.bye_count }} 次 · {{ item.status === 'ACTIVE' ? '参赛中' : '已退赛' }}</small></span><button v-if="item.status === 'ACTIVE'" type="button" :disabled="busy || !withdrawalOpen" @click="withdraw(item)">退赛</button></article></section>
        </div>
      </template>
    </section>

    <section v-if="tournament && section === 'playoffs'" class="playoff-admin">
      <div v-if="!['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.status)" class="empty-state">完成瑞士轮后开放淘汰赛管理。</div>
      <template v-else>
        <div class="swiss-operation-bar">
          <div><h2>淘汰赛签表</h2><p>Top N 按瑞士轮最终排名固定入位，不允许重新抽签或交换种子。</p></div>
          <div class="form-actions">
            <button v-if="tournament.status !== 'ENDED' && (!latestPlayoffRound || (latestPlayoffRound.status === 'COMPLETED' && latestPlayoffRound.bracket_size > 2))" class="button primary" type="button" :disabled="busy" @click="generatePlayoffStage">生成下一阶段</button>
            <button v-if="latestPlayoffRound?.status === 'DRAFT'" class="button primary" type="button" :disabled="busy" @click="publishPlayoffStage">正式发布{{ latestPlayoffRound.name }}</button>
            <button v-if="tournament.status === 'ELIMINATION' && playoff?.awaiting_tournament_end" class="button primary" type="button" :disabled="busy" @click="endTournament">结束赛事并锁定结果</button>
          </div>
        </div>
        <div v-if="playoff?.champion_nickname" class="champion-strip"><span>CHAMPION</span><strong>{{ playoff.champion_nickname }}</strong><small>{{ playoff.awaiting_tournament_end ? '决赛已完成，等待主办方手动结束赛事。' : '赛事已结束，全部结果已永久锁定。' }}</small></div>
        <label v-if="latestPlayoffRound?.status !== 'DRAFT'" class="forfeit-reason"><span>主办方判负原因</span><input v-model.trim="forfeitReason" maxlength="500" placeholder="填写选手无法继续参赛的原因" /></label>
        <section v-if="pendingPlayoffForfeit" class="forfeit-confirmation" role="dialog" aria-labelledby="forfeit-confirmation-title">
          <div>
            <strong id="forfeit-confirmation-title">确认主办方裁定</strong>
            <p>将判“{{ pendingPlayoffForfeit.loserNickname }}”负、“{{ pendingPlayoffForfeit.winnerNickname }}”胜，并覆盖双方当前提交的赛果。</p>
            <small>判负原因：{{ pendingPlayoffForfeit.reason }}</small>
          </div>
          <div class="form-actions">
            <button class="button secondary small" type="button" :disabled="busy" @click="cancelPlayoffForfeit">取消</button>
            <button class="button primary small" type="button" :disabled="busy" @click="confirmPlayoffForfeit">确定判负</button>
          </div>
        </section>
        <div v-if="playoff?.rounds.length" class="playoff-bracket admin-bracket" :style="{ '--round-count': playoff.rounds.length }">
          <section v-for="round in playoff.rounds" :key="round.id" class="bracket-round">
            <header><strong>{{ round.name }}</strong><span>{{ swissRoundStatusText[round.status] }}</span></header>
            <div class="bracket-match-list">
              <article v-for="match in round.matches" :key="match.id" class="bracket-match admin-bracket-match">
                <div :class="{ winner: match.winner_id === match.player_a_id }"><span>#{{ match.seed_a }}</span><strong>{{ match.player_a_nickname }}</strong><i>{{ match.player_a_result === 'WIN' ? '胜' : match.player_a_result === 'LOSS' ? '负' : '' }}</i></div>
                <div :class="{ winner: match.winner_id === match.player_b_id }"><span>#{{ match.seed_b }}</span><strong>{{ match.player_b_nickname }}</strong><i>{{ match.player_b_result === 'WIN' ? '胜' : match.player_b_result === 'LOSS' ? '负' : '' }}</i></div>
                <footer><span>{{ matchStatusText[match.status] }}</span><div v-if="round.status !== 'DRAFT' && !match.result_locked" class="row-actions"><button type="button" :disabled="busy" @click="requestPlayoffForfeit(match, match.player_a_id)">判 A 负</button><button type="button" :disabled="busy" @click="requestPlayoffForfeit(match, match.player_b_id)">判 B 负</button></div></footer>
              </article>
            </div>
          </section>
        </div>
        <p v-else class="empty-state">全部瑞士轮完成后，点击“生成下一阶段”创建 Top {{ tournament.playoff_size }} 固定种子签表。</p>
      </template>
    </section>

    <section v-if="tournament && section === 'decks-report'" class="phase5-admin">
      <div v-if="tournament.status !== 'ENDED'" class="empty-state">赛事结束后开放四强卡组审核与周报发布。</div>
      <template v-else>
        <div class="swiss-operation-bar"><div><h2>四强卡组截图</h2><p>截图审核通过后即锁定；4/4 全部通过才允许生成周报。</p></div><strong>{{ deckSubmissions?.approved_count ?? 0 }} / 4 已通过</strong></div>
        <label class="forfeit-reason"><span>退回原因</span><input v-model.trim="deckReturnReason" maxlength="500" placeholder="填写需要选手重新上传的原因" /></label>
        <div class="deck-review-grid">
          <article v-for="item in deckSubmissions?.items" :key="item.id" class="deck-review-card">
            <header><span>第 {{ item.placement }} 名</span><strong>{{ item.nickname }}</strong><i :class="['status-badge', `deck-${item.status.toLowerCase()}`]">{{ deckStatusText[item.status] }}</i></header>
            <img v-if="item.image_url" :src="item.image_url" :alt="`${item.nickname} 的卡组截图`" />
            <div v-else class="deck-image-empty">等待选手上传</div>
            <p v-if="item.review_note">上次退回：{{ item.review_note }}</p>
            <footer v-if="item.status === 'PENDING_REVIEW'" class="row-actions"><button type="button" :disabled="busy" @click="reviewDeck(item, 'approve')">审核通过</button><button type="button" :disabled="busy" @click="reviewDeck(item, 'return')">退回重传</button></footer>
          </article>
        </div>

        <div class="report-admin-heading"><div><p class="section-kicker">WEEKLY REPORT</p><h2>赛事周报</h2><p>固定模板只读取已锁定的赛事事实，不提供自由编辑。</p></div><div class="form-actions"><button v-if="!weeklyReport" class="button primary" type="button" :disabled="busy || deckSubmissions?.approved_count !== 4" @click="generateWeeklyReport">生成周报草稿</button><button v-if="weeklyReport?.status === 'DRAFT'" class="button primary" type="button" :disabled="busy" @click="publishWeeklyReport">发布周报</button><RouterLink v-if="weeklyReport?.status === 'PUBLISHED'" class="button secondary" :to="`/reports/${weeklyReport.id}`">查看已发布周报</RouterLink></div></div>
        <WeeklyReportContent v-if="weeklyReport" :report="weeklyReport" />
        <p v-else class="empty-state compact">四强截图 4/4 审核通过后可生成周报草稿。</p>
      </template>
    </section>

    <section v-if="tournament && section === 'notifications'" class="notice-admin-section">
      <div class="settings-heading"><div><h2>赛事通知</h2><p>只向本届正式参赛玩家发送临时运营信息，不用于自动播报对阵或赛果。</p></div></div>
      <form class="content-form notice-form" @submit.prevent="sendTournamentNotice">
        <label><span>通知标题</span><input v-model.trim="noticeForm.title" minlength="2" maxlength="120" required /></label>
        <label><span>通知正文</span><textarea v-model.trim="noticeForm.body" minlength="2" maxlength="5000" rows="7" required /></label>
        <button class="button primary" type="submit" :disabled="busy">发送给正式参赛玩家</button>
      </form>
    </section>

    <section v-if="tournament && section === 'audit'" class="audit-admin-section">
      <div class="settings-heading"><div><h2>操作日志</h2><p>本届赛事中影响公平性、审核结果和不可逆状态的关键操作。</p></div><strong>{{ auditLogs?.total ?? 0 }} 条</strong></div>
      <div v-if="auditLogs?.items.length" class="audit-list">
        <article v-for="item in auditLogs.items" :key="item.id" class="audit-row"><time>{{ formatAuditTime(item.created_at) }}</time><div><strong>{{ item.action_type }}</strong><p>{{ item.operator_nickname }} · {{ item.target_type }} / {{ item.target_id }}</p></div><details><summary>数据变化</summary><pre>{{ JSON.stringify({ before: item.before_json, after: item.after_json }, null, 2) }}</pre></details></article>
      </div>
      <p v-else class="empty-state">尚无本届赛事审计记录。</p>
    </section>
  </div>
</template>
