<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { apiGet, apiPatch, apiPost } from '@/api/client'
import ConfirmFormDialog from '@/components/ConfirmFormDialog.vue'
import FormMessage from '@/components/FormMessage.vue'
import MatchHistoryList from '@/components/MatchHistoryList.vue'
import PlayoffResultsTree from '@/components/PlayoffResultsTree.vue'
import { TOURNAMENT_AUDIT_VIEW_ENABLED, TOURNAMENT_NOTIFICATIONS_ENABLED } from '@/config/features'
import { useAuthStore } from '@/stores/auth'
import type { BanlistVersion, ListResponse } from '@/types/content'
import type { DeckSubmission, DeckSubmissionList, WeeklyReport } from '@/types/report'
import { deckPlacementText, deckStatusText } from '@/types/report'
import type { AuditLogListResponse, MessageSendResponse } from '@/types/message'
import { auditActionText } from '@/types/message'
import type {
  MatchHistoryItem, Participant, PlayoffMatch, PlayoffOverview, PlayoffRound, Registration, RegistrationBulkApproveResponse, RegistrationListResponse, SubmittedResult, SwissMatch, SwissOverview, SwissRound, Tournament,
} from '@/types/tournament'
import { matchStatusText, registrationStatusText, swissRoundStatusText, tournamentStatusText } from '@/types/tournament'

type PendingPlayoffResolution = {
  match: PlayoffMatch
  winnerId: string | null
  reason: string
  reasonOpen: boolean
}

type PendingSwissResolution = {
  match: SwissMatch
  winnerId: string | null
  reason: string
  reasonOpen: boolean
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
const pendingPlayoffResolution = ref<PendingPlayoffResolution | null>(null)
const pendingSwissResolution = ref<PendingSwissResolution | null>(null)
const deckSubmissions = ref<DeckSubmissionList | null>(null)
const weeklyReport = ref<WeeklyReport | null>(null)
const auditLogs = ref<AuditLogListResponse | null>(null)
const noticeForm = reactive({ title: '', body: '' })
const previewDeck = ref<DeckSubmission | null>(null)
const deckPreviewCloseButton = ref<HTMLButtonElement | null>(null)
const matchFilter = ref<'ALL' | 'WAITING' | 'CONFLICT' | 'COMPLETED'>('ALL')
const playerTab = ref<'registrations' | 'participants'>('registrations')
const competitionStage = ref<'swiss' | 'playoff'>('swiss')
const selectedSwissRoundNo = ref<number | null>(null)
const selectedPlayoffRoundId = ref<string | null>(null)
const selectedRankingParticipantId = ref<string | null>(null)
const swapFirst = ref('')
const swapSecond = ref('')
const error = ref('')
const message = ref('')
const busy = ref(false)
const bulkApprovalOpen = ref(false)
const startTournamentOpen = ref(false)
const publishSwissRoundOpen = ref(false)
const publishPlayoffStageOpen = ref(false)
const tournamentId = computed(() => String(route.params.id))
const section = computed(() => String(route.params.section || 'settings'))
const coreLocked = computed(() => tournament.value ? ['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.value.status) : false)
const latestRound = computed<SwissRound | null>(() => swissRounds.value[swissRounds.value.length - 1] ?? null)
const selectedSwissRound = computed<SwissRound | null>(() =>
  swissRounds.value.find((item) => item.round_no === selectedSwissRoundNo.value) ?? latestRound.value,
)
const filteredMatches = computed<SwissMatch[]>(() => {
  const matches = selectedSwissRound.value?.matches ?? []
  if (selectedSwissRound.value?.status === 'DRAFT') return matches
  return matchFilter.value === 'ALL' ? matches : matches.filter((item) => item.status === matchFilter.value)
})
const draftParticipantIds = computed<string[]>(() => {
  if (latestRound.value?.status !== 'DRAFT') return []
  return latestRound.value.matches.flatMap((item: SwissMatch) =>
    [item.player_a_id, item.player_b_id].filter((id): id is string => Boolean(id)),
  )
})
const tournamentStarted = computed(() => tournament.value ? ['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.value.status) : false)
const registrationActionsOpen = computed(() => tournament.value?.status === 'REGISTRATION')
const activeParticipantCount = computed(() => participants.value.filter((item) => item.status === 'ACTIVE').length)
const withdrawnParticipantCount = computed(() => participants.value.filter((item) => item.status === 'WITHDRAWN').length)
const pendingRegistrationCount = computed(() => registrations.value.filter((item) => item.status === 'PENDING').length)
const withdrawalOpen = computed(() => tournament.value?.status === 'SWISS' && (!latestRound.value || ['DRAFT', 'COMPLETED'].includes(latestRound.value.status)))
const latestPlayoffRound = computed(() => playoff.value?.rounds[playoff.value.rounds.length - 1] ?? null)
const selectedPlayoffRound = computed<PlayoffRound | null>(() =>
  playoff.value?.rounds.find((round) => round.id === selectedPlayoffRoundId.value) ?? latestPlayoffRound.value,
)
const filteredPlayoffMatches = computed<PlayoffMatch[]>(() => {
  const matches = selectedPlayoffRound.value?.matches ?? []
  if (selectedPlayoffRound.value?.status === 'DRAFT') return matches
  return matchFilter.value === 'ALL' ? matches : matches.filter((match) => match.status === matchFilter.value)
})
const swissRecords = computed(() => new Map(
  (swissOverview.value?.rankings ?? []).map((item) => [item.participant_id, `${item.wins}-${item.losses}`]),
))
const selectedRankingHistory = computed<MatchHistoryItem[]>(() => {
  const participantId = selectedRankingParticipantId.value
  if (!participantId) return []
  return swissRounds.value
    .filter((round) => round.status === 'COMPLETED')
    .flatMap((round) => round.matches
      .filter((match) => match.status === 'COMPLETED' && [match.player_a_id, match.player_b_id].includes(participantId))
      .map((match) => ({
        id: match.id,
        stage: 'SWISS' as const,
        stage_order: 1,
        round_no: round.round_no,
        round_name: `第 ${round.round_no} 轮瑞士轮`,
        table_no: match.table_no,
        player_a_id: match.player_a_id,
        player_a_nickname: match.player_a_nickname,
        player_b_id: match.player_b_id,
        player_b_nickname: match.player_b_nickname,
        winner_id: match.winner_id,
        status: match.status,
        my_participant_id: participantId,
      })))
    .sort((a, b) => b.round_no - a.round_no || b.table_no - a.table_no)
})
const form = reactive({ name: '', description: '', planned_start_at: '', max_players: 32, swiss_rounds: 5, playoff_size: 8, banlist_version_id: '' })

const swissRecord = (participantId: string) => swissRecords.value.get(participantId) ?? '0-0'

function toggleRankingHistory(participantId: string) {
  selectedRankingParticipantId.value = selectedRankingParticipantId.value === participantId ? null : participantId
}

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
  if (section.value === 'players') {
    playerTab.value = ['DRAFT', 'REGISTRATION'].includes(item.status) ? 'registrations' : 'participants'
    await loadPlayerManagement(item)
  }
  if (['matches', 'results'].includes(section.value) && ['SWISS', 'ELIMINATION', 'ENDED'].includes(item.status)) {
    competitionStage.value = route.query.stage === 'playoff' || route.query.stage === 'swiss'
      ? route.query.stage
      : (['ELIMINATION', 'ENDED'].includes(item.status) ? 'playoff' : 'swiss')
    await loadCompetitionData()
  }
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

async function loadParticipants() {
  participants.value = await apiGet<Participant[]>(
    `/admin/tournaments/${tournamentId.value}/participants`, undefined, authStore.token,
  )
}

async function loadSwissOverview() {
  swissOverview.value = await apiGet<SwissOverview>(`/tournaments/${tournamentId.value}/swiss`)
}

async function loadSwissRounds() {
  const isActiveSwiss = tournament.value?.status === 'SWISS'
  swissRounds.value = await apiGet<SwissRound[]>(
    isActiveSwiss
      ? `/admin/tournaments/${tournamentId.value}/swiss/rounds`
      : `/tournaments/${tournamentId.value}/swiss/rounds`,
    undefined,
    isActiveSwiss ? authStore.token : undefined,
  )
}

async function loadPlayerManagement(item: Tournament) {
  const requests: Promise<void>[] = [loadRegistrations(), loadParticipants()]
  if (['SWISS', 'ELIMINATION', 'ENDED'].includes(item.status)) requests.push(loadSwissOverview())
  if (item.status === 'SWISS') requests.push(loadSwissRounds())
  await Promise.all(requests)
}

async function loadSwiss() {
  await Promise.all([loadSwissRounds(), loadSwissOverview(), loadParticipants()])
  selectedSwissRoundNo.value = latestRound.value?.round_no ?? null
  swapFirst.value = ''
  swapSecond.value = ''
}

async function loadPlayoffs() {
  playoff.value = await apiGet<PlayoffOverview>(
    `/admin/tournaments/${tournamentId.value}/playoffs`, undefined, authStore.token,
  )
  if (!playoff.value.rounds.some((round) => round.id === selectedPlayoffRoundId.value)) {
    selectedPlayoffRoundId.value = playoff.value.rounds[playoff.value.rounds.length - 1]?.id ?? null
  }
}

async function loadCompetitionData() {
  await Promise.all([loadSwiss(), loadPlayoffs()])
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

function requestMatchResolution(match: SwissMatch) {
  error.value = ''
  pendingSwissResolution.value = { match, winnerId: null, reason: '', reasonOpen: false }
}

function cancelMatchResolution() {
  pendingSwissResolution.value = null
  error.value = ''
}

function matchResolutionActionText(match: SwissMatch | PlayoffMatch) {
  if (match.status === 'COMPLETED') return '纠正赛果'
  if (match.status === 'CONFLICT') return '处理冲突'
  return '处理未提交'
}

function displayedMatchResult(match: SwissMatch | PlayoffMatch, participantId: string | null): SubmittedResult | null {
  if (!participantId) return null
  if (match.status === 'COMPLETED') {
    if (!match.winner_id) return null
    return match.winner_id === participantId ? 'WIN' : 'LOSS'
  }
  if (match.player_a_id === participantId) return match.player_a_result
  if (match.player_b_id === participantId) return match.player_b_result
  return null
}

function displayedMatchResultText(match: SwissMatch | PlayoffMatch, participantId: string | null): string {
  const result = displayedMatchResult(match, participantId)
  return result === 'WIN' ? '胜' : result === 'LOSS' ? '负' : ''
}

function matchResolutionTitle(match: SwissMatch | PlayoffMatch) {
  if (match.status === 'COMPLETED') return `纠正第 ${match.table_no} 桌赛果`
  if (match.status === 'CONFLICT') return `处理第 ${match.table_no} 桌冲突`
  return `处理第 ${match.table_no} 桌未提交`
}

function resolutionSummary(match: SwissMatch | PlayoffMatch, winnerId: string | null) {
  if (!winnerId) return ''
  const winnerNickname = winnerId === match.player_a_id ? match.player_a_nickname : match.player_b_nickname
  const loserNickname = winnerId === match.player_a_id ? match.player_b_nickname : match.player_a_nickname
  return `将记录：${winnerNickname} 胜 / ${loserNickname} 负`
}

function canConfirmResolution(pending: PendingSwissResolution | PendingPlayoffResolution) {
  return Boolean(pending.winnerId)
}

async function confirmSwissResolution() {
  const pending = pendingSwissResolution.value
  if (!pending?.winnerId || !canConfirmResolution(pending)) return
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/matches/${pending.match.id}/resolve`, {
      winner_id: pending.winnerId,
      reason: pending.reason.trim() || null,
    }, authStore.token)
    message.value = '赛果已由赛事主办方确认。'
    pendingSwissResolution.value = null
    await loadSwiss()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛果裁定失败'
  } finally { busy.value = false }
}

async function withdraw(participant: Participant) {
  if (!window.confirm(`确认将“${participant.nickname_snapshot}”强制退赛？历史赛果会保留。`)) return
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/tournaments/${tournamentId.value}/participants/${participant.id}/withdraw`, {}, authStore.token)
    message.value = '选手已退赛；若存在未发布预览，系统已自动作废。'
    if (tournament.value) await loadPlayerManagement(tournament.value)
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
    selectedPlayoffRoundId.value = latestPlayoffRound.value?.id ?? null
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '淘汰阶段生成失败'
  } finally { busy.value = false }
}

function requestPlayoffStagePublish() {
  if (!latestPlayoffRound.value || latestPlayoffRound.value.status !== 'DRAFT') return
  error.value = ''
  publishPlayoffStageOpen.value = true
}

function cancelPlayoffStagePublish() {
  if (!busy.value) publishPlayoffStageOpen.value = false
}

async function publishPlayoffStage() {
  if (!latestPlayoffRound.value || latestPlayoffRound.value.status !== 'DRAFT') {
    publishPlayoffStageOpen.value = false
    return
  }
  busy.value = true
  error.value = ''
  try {
    await apiPost(
      `/admin/tournaments/${tournamentId.value}/playoffs/rounds/${latestPlayoffRound.value.id}/publish`, {}, authStore.token,
    )
    message.value = `${latestPlayoffRound.value.name}已正式发布。`
    await Promise.all([loadPlayoffs(), loadTournamentSummary()])
    publishPlayoffStageOpen.value = false
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '淘汰阶段发布失败'
  } finally { busy.value = false }
}

async function endTournament() {
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
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/deck-submissions/${item.id}/${action}`, action === 'return'
      ? { reason: '' }
      : {}, authStore.token)
    message.value = action === 'approve' ? '卡组截图已审核通过并锁定。' : '截图已退回，等待选手重新上传。'
    await loadPhase5()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '卡组截图审核失败'
  } finally { busy.value = false }
}

function openDeckPreview(item: DeckSubmission) {
  if (item.image_url) previewDeck.value = item
}

function closeDeckPreview() {
  previewDeck.value = null
}

async function generateWeeklyReport() {
  busy.value = true
  error.value = ''
  try {
    weeklyReport.value = await apiPost<WeeklyReport>(
      `/admin/tournaments/${tournamentId.value}/reports/generate`, {}, authStore.token,
    )
    message.value = '周报已生成并发布。'
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '周报生成失败'
  } finally { busy.value = false }
}

function requestPlayoffResolution(match: PlayoffMatch) {
  error.value = ''
  pendingPlayoffResolution.value = { match, winnerId: null, reason: '', reasonOpen: false }
}

function cancelPlayoffResolution() {
  pendingPlayoffResolution.value = null
}

async function confirmPlayoffResolution() {
  const pending = pendingPlayoffResolution.value
  if (!pending?.winnerId || !canConfirmResolution(pending)) return
  const loserId = pending.winnerId === pending.match.player_a_id
    ? pending.match.player_b_id
    : pending.match.player_a_id
  busy.value = true
  error.value = ''
  try {
    await apiPost(`/admin/playoffs/matches/${pending.match.id}/forfeit`, {
      loser_id: loserId,
      reason: pending.reason.trim() || null,
    }, authStore.token)
    pendingPlayoffResolution.value = null
    message.value = '赛果已由赛事主办方确认并写入审计记录。'
    await loadPlayoffs()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛果裁定失败'
  } finally { busy.value = false }
}

watch(section, async (value) => {
  if (value === 'players' && tournament.value) {
    playerTab.value = ['DRAFT', 'REGISTRATION'].includes(tournament.value.status) ? 'registrations' : 'participants'
    await loadPlayerManagement(tournament.value)
  }
  if (['matches', 'results'].includes(value) && tournament.value && ['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.value.status)) await loadCompetitionData()
  if (value === 'decks-report' && tournament.value?.status === 'ENDED') await loadPhase5()
  if (value === 'audit') await loadAuditLogs()
})
watch(previewDeck, async (item) => {
  if (!item) return
  await nextTick()
  deckPreviewCloseButton.value?.focus()
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
      <RouterLink :to="`/tournaments/${tournamentId}/manage/players`">选手</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/matches`">对阵</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/results`">赛果</RouterLink>
      <RouterLink :to="`/tournaments/${tournamentId}/manage/decks-report`">卡组与周报</RouterLink>
      <RouterLink v-if="TOURNAMENT_NOTIFICATIONS_ENABLED" :to="`/tournaments/${tournamentId}/manage/notifications`">赛事通知</RouterLink>
      <RouterLink v-if="TOURNAMENT_AUDIT_VIEW_ENABLED" :to="`/tournaments/${tournamentId}/manage/audit`">操作日志</RouterLink>
    </nav>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />
    <Teleport to="body">
      <div v-if="previewDeck?.image_url" class="form-dialog-backdrop" @mousedown.self="closeDeckPreview">
        <section class="deck-image-preview-dialog" role="dialog" aria-modal="true" :aria-label="`${previewDeck.nickname}的卡组大图预览`" @keydown.esc.prevent="closeDeckPreview">
          <header>
            <div><p class="section-kicker">DECK PREVIEW</p><h2>{{ previewDeck.nickname }}的卡组截图</h2></div>
            <button ref="deckPreviewCloseButton" class="button secondary small" type="button" @click="closeDeckPreview">关闭预览</button>
          </header>
          <img :src="previewDeck.image_url" :alt="`${previewDeck.nickname} 的卡组截图大图`" />
        </section>
      </div>
    </Teleport>
    <ConfirmFormDialog
      v-if="bulkApprovalOpen && tournament"
      title="批量通过报名"
      :description="`将一次通过全部 ${tournament.pending_count} 名待审核选手。`"
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
    <ConfirmFormDialog
      v-if="publishPlayoffStageOpen && latestPlayoffRound"
      :title="`正式发布${latestPlayoffRound.name}`"
      description="发布后本阶段签表不可修改，选手将可以查看对手并提交赛果。"
      confirm-text="确认正式发布"
      :busy="busy"
      :error="error"
      @cancel="cancelPlayoffStagePublish"
      @confirm="publishPlayoffStage"
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

    <section v-if="tournament && section === 'players'" class="player-management">
      <div class="settings-heading">
        <div><h2>选手管理</h2><p>统一管理报名审核与开赛后的正式参赛名单。</p></div>
      </div>
      <dl class="player-summary" aria-label="选手数量概览">
        <div><dt>报名</dt><dd>{{ registrations.length }}</dd></div>
        <div><dt>待审核</dt><dd>{{ pendingRegistrationCount }}</dd></div>
        <div><dt>正式选手</dt><dd>{{ participants.length }}</dd></div>
        <div><dt>已退赛</dt><dd>{{ withdrawnParticipantCount }}</dd></div>
      </dl>
      <nav class="player-tabs" role="tablist" aria-label="选手管理内容">
        <button type="button" role="tab" :aria-selected="playerTab === 'registrations'" :class="{ active: playerTab === 'registrations' }" @click="playerTab = 'registrations'">报名申请 <small>{{ registrations.length }}</small></button>
        <button type="button" role="tab" :aria-selected="playerTab === 'participants'" :class="{ active: playerTab === 'participants' }" @click="playerTab = 'participants'">正式选手 <small>{{ participants.length }}</small></button>
      </nav>

      <div v-if="playerTab === 'registrations'" role="tabpanel">
        <div class="player-section-heading">
          <p>审核通过人数不会超过 {{ tournament.max_players }} 人。<span v-if="!registrationActionsOpen">当前赛事已关闭报名，申请记录仅供查看。</span></p>
          <div class="registration-heading-actions">
            <button v-if="registrationActionsOpen" class="button primary small" type="button" :disabled="busy || pendingRegistrationCount === 0" @click="requestPendingApproval">批量通过</button>
            <span>待审核 {{ pendingRegistrationCount }}</span>
          </div>
        </div>
        <p v-if="!registrations.length" class="empty-state">暂无报名记录。</p>
        <div v-else class="player-table-wrap">
          <table class="player-table">
            <thead><tr><th>昵称</th><th>报名状态</th><th>申请时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in registrations" :key="item.id">
                <td><strong>{{ item.nickname }}</strong></td>
                <td><span :class="['status-badge', `registration-${item.status.toLowerCase()}`]">{{ registrationStatusText[item.status] }}</span></td>
                <td><time>{{ formatAuditTime(item.created_at) }}</time></td>
                <td>
                  <div v-if="registrationActionsOpen" class="row-actions">
                    <template v-if="item.status === 'PENDING'"><button type="button" :disabled="busy" @click="review(item, 'approve')">通过</button><button type="button" :disabled="busy" @click="review(item, 'reject')">拒绝</button></template>
                    <button v-if="item.status === 'APPROVED'" type="button" :disabled="busy" @click="review(item, 'cancel')">取消</button>
                    <button v-if="['REJECTED','CANCELED'].includes(item.status)" type="button" :disabled="busy" @click="review(item, 'restore')">恢复为已通过</button>
                  </div>
                  <span v-else class="table-placeholder">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else role="tabpanel">
        <p v-if="!tournamentStarted" class="empty-state">赛事开始后，系统会根据已通过的报名生成正式选手名单。</p>
        <template v-else>
          <div class="player-section-heading">
            <p><template v-if="tournament.status === 'SWISS'">仅轮次结束且下一轮未发布时可强制退赛；未发布的预览将自动作废。</template><template v-else>当前阶段的正式选手名单仅供查看。</template></p>
            <span>参赛中 {{ activeParticipantCount }} · 已退赛 {{ withdrawnParticipantCount }}</span>
          </div>
          <p v-if="!participants.length" class="empty-state">暂无正式选手。</p>
          <div v-else class="player-table-wrap">
            <table class="player-table">
              <thead><tr><th>昵称</th><th>参赛状态</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="item in participants" :key="item.id">
                  <td><strong>{{ item.nickname_snapshot }}</strong></td>
                  <td><span :class="['status-badge', `participant-${item.status.toLowerCase()}`]">{{ item.status === 'ACTIVE' ? '参赛中' : '已退赛' }}</span></td>
                  <td>
                    <button v-if="item.status === 'ACTIVE' && tournament.status === 'SWISS'" class="text-action" type="button" :disabled="busy || !withdrawalOpen" :title="withdrawalOpen ? '强制退赛' : '当前轮已发布，请先完成本轮'" @click="withdraw(item)">强制退赛</button>
                    <span v-else class="table-placeholder">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </section>

    <section v-if="tournament && ['matches', 'results'].includes(section)" class="competition-admin">
      <header class="competition-heading">
        <div>
          <p class="section-kicker">{{ section === 'matches' ? 'MATCHES' : 'RESULTS' }}</p>
          <h2>{{ section === 'matches' ? '对阵' : '赛果' }}</h2>
          <p>{{ section === 'matches' ? '查看并管理每一场比赛明细。' : '查看瑞士轮排名与淘汰赛晋级结果。' }}</p>
        </div>
      </header>
      <nav class="competition-stage-tabs" role="tablist" :aria-label="`${section === 'matches' ? '对阵' : '赛果'}阶段`">
        <button type="button" role="tab" :class="{ active: competitionStage === 'swiss' }" :aria-selected="competitionStage === 'swiss'" @click="competitionStage = 'swiss'">瑞士轮</button>
        <button type="button" role="tab" :class="{ active: competitionStage === 'playoff' }" :aria-selected="competitionStage === 'playoff'" @click="competitionStage = 'playoff'">淘汰赛</button>
      </nav>

      <template v-if="section === 'matches' && competitionStage === 'swiss'">
        <div v-if="!['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.status)" class="empty-state">赛事进入瑞士轮后显示对阵。</div>
        <template v-else>
          <div v-if="tournament.status === 'SWISS'" class="swiss-operation-bar">
            <div><h3>瑞士轮对阵</h3><p>生成只是预览；正式发布后对阵不可修改，并锁定上一轮赛果。</p></div>
            <div class="form-actions">
              <button v-if="!latestRound || latestRound.status === 'COMPLETED'" class="button primary" type="button" :disabled="busy || (swissOverview?.completed_rounds ?? 0) >= (tournament.swiss_rounds ?? 0)" @click="swissAction('generate')">生成下一轮</button>
              <template v-if="latestRound?.status === 'DRAFT'">
                <button class="button secondary" type="button" :disabled="busy" @click="swissAction('regenerate')">重新生成</button>
                <button class="button primary" type="button" :disabled="busy" @click="requestSwissRoundPublish">正式发布</button>
              </template>
            </div>
          </div>

          <nav v-if="swissRounds.length" class="competition-round-tabs" role="tablist" aria-label="瑞士轮轮次">
            <button v-for="round in swissRounds" :key="round.id" type="button" role="tab" :class="{ active: selectedSwissRound?.id === round.id }" :aria-selected="selectedSwissRound?.id === round.id" @click="selectedSwissRoundNo = round.round_no">第 {{ round.round_no }} 轮</button>
          </nav>

          <div v-if="selectedSwissRound" class="round-admin-heading">
            <div><strong>第 {{ selectedSwissRound.round_no }} 轮</strong><span :class="['status-badge', `round-${selectedSwissRound.status.toLowerCase()}`]">{{ swissRoundStatusText[selectedSwissRound.status] }}</span></div>
            <label v-if="selectedSwissRound.status !== 'DRAFT'">筛选
              <select v-model="matchFilter"><option value="ALL">全部</option><option value="WAITING">未完成</option><option value="CONFLICT">赛果冲突</option><option value="COMPLETED">已完成</option></select>
            </label>
          </div>

          <div v-if="selectedSwissRound?.id === latestRound?.id && selectedSwissRound?.status === 'DRAFT'" class="swap-panel">
            <strong>交换选手 / 更换 BYE</strong>
            <select v-model="swapFirst"><option value="">选择第一名选手</option><option v-for="item in draftParticipantIds" :key="item" :value="item">{{ participants.find((participant) => participant.id === item)?.nickname_snapshot }}</option></select>
            <select v-model="swapSecond"><option value="">选择第二名选手</option><option v-for="item in draftParticipantIds" :key="item" :value="item">{{ participants.find((participant) => participant.id === item)?.nickname_snapshot }}</option></select>
            <button class="button secondary small" type="button" :disabled="busy || !swapFirst || !swapSecond || swapFirst === swapSecond" @click="swapPlayers">交换位置</button>
          </div>

          <div v-if="selectedSwissRound" class="admin-match-list">
            <template v-for="match in filteredMatches" :key="match.id">
              <article :class="['admin-match-row', { 'admin-match-row-preview': selectedSwissRound.status === 'DRAFT' }]">
                <span class="match-table-no">第 {{ match.table_no }} 桌</span>
                <div class="admin-match-players">
                  <span :class="['admin-match-player', 'admin-match-player-a', { winner: match.winner_id === match.player_a_id }]">
                    <strong>{{ match.player_a_nickname }}</strong><small v-if="displayedMatchResult(match, match.player_a_id)" :class="['admin-result-mark', `submission-${displayedMatchResult(match, match.player_a_id)?.toLowerCase()}`]">{{ displayedMatchResultText(match, match.player_a_id) }}</small><em v-if="selectedSwissRound.status === 'DRAFT'">（{{ swissRecord(match.player_a_id) }}）</em>
                  </span>
                  <i class="admin-match-versus">{{ match.player_b_id ? 'VS' : 'BYE' }}</i>
                  <span :class="['admin-match-player', 'admin-match-player-b', { winner: match.winner_id === match.player_b_id }]">
                    <small v-if="displayedMatchResult(match, match.player_b_id)" :class="['admin-result-mark', `submission-${displayedMatchResult(match, match.player_b_id)?.toLowerCase()}`]">{{ displayedMatchResultText(match, match.player_b_id) }}</small><strong>{{ match.player_b_nickname || '轮空' }}</strong><em v-if="selectedSwissRound.status === 'DRAFT' && match.player_b_id">（{{ swissRecord(match.player_b_id) }}）</em>
                  </span>
                </div>
                <small v-if="selectedSwissRound.status === 'DRAFT' && match.warnings.length" class="admin-match-warning">{{ match.warnings.join(' · ') }}</small>
                <div v-if="selectedSwissRound.status !== 'DRAFT'" class="admin-match-outcome">
                  <span :class="['status-badge', `match-${match.status.toLowerCase()}`]">{{ matchStatusText[match.status] }}</span>
                  <div v-if="tournament.status === 'SWISS' && match.player_b_id && !match.result_locked" class="row-actions"><button type="button" :aria-label="matchResolutionActionText(match)" :title="matchResolutionActionText(match)" :disabled="busy" @click="requestMatchResolution(match)">处理</button></div>
                </div>
              </article>
              <section v-if="pendingSwissResolution?.match.id === match.id" class="forfeit-confirmation swiss-resolution-confirmation" role="dialog" :aria-labelledby="`swiss-resolution-title-${match.id}`">
                <div class="match-resolution-toolbar">
                  <strong :id="`swiss-resolution-title-${match.id}`">{{ matchResolutionTitle(match) }}</strong>
                  <div class="match-resolution-winners">
                    <button :class="['button', 'small', pendingSwissResolution.winnerId === match.player_a_id ? 'primary' : 'secondary']" type="button" :disabled="busy" @click="pendingSwissResolution.winnerId = match.player_a_id">判 {{ match.player_a_nickname }} 胜</button>
                    <button :class="['button', 'small', pendingSwissResolution.winnerId === match.player_b_id ? 'primary' : 'secondary']" type="button" :disabled="busy" @click="pendingSwissResolution.winnerId = match.player_b_id">判 {{ match.player_b_nickname }} 胜</button>
                  </div>
                  <div class="form-actions swiss-resolution-actions">
                    <button class="button secondary small" type="button" :disabled="busy" @click="cancelMatchResolution">取消</button>
                    <button class="button primary small" type="button" :disabled="busy || !canConfirmResolution(pendingSwissResolution)" @click="confirmSwissResolution">确认裁定</button>
                  </div>
                </div>
                <div class="match-resolution-meta">
                  <small class="match-resolution-summary">{{ pendingSwissResolution.winnerId ? resolutionSummary(match, pendingSwissResolution.winnerId) : '请选择获胜者' }}</small>
                  <button class="match-resolution-reason-toggle" type="button" :aria-expanded="pendingSwissResolution.reasonOpen" :aria-controls="`swiss-resolution-reason-${match.id}`" @click="pendingSwissResolution.reasonOpen = !pendingSwissResolution.reasonOpen">{{ pendingSwissResolution.reasonOpen ? '收起裁定原因' : '＋填写裁定原因（选填）' }}</button>
                </div>
                <label v-if="pendingSwissResolution.reasonOpen" :id="`swiss-resolution-reason-${match.id}`" class="match-resolution-reason"><span>裁定原因（选填）</span><input v-model.trim="pendingSwissResolution.reason" maxlength="500" placeholder="可不填" /></label>
              </section>
            </template>
            <p v-if="!filteredMatches.length" class="empty-state compact">该筛选下没有对阵。</p>
          </div>
          <p v-else class="empty-state">尚未生成瑞士轮对阵。</p>
        </template>
      </template>

      <template v-else-if="section === 'matches' && competitionStage === 'playoff'">
        <div v-if="!['SWISS', 'ELIMINATION', 'ENDED'].includes(tournament.status)" class="empty-state">完成瑞士轮后开放淘汰赛管理。</div>
        <template v-else>
          <div class="swiss-operation-bar">
            <div><h3>淘汰赛对阵</h3><p>按阶段查看和处理每场对局；Top N 按瑞士轮最终排名固定入位。</p></div>
            <div class="form-actions">
              <button v-if="tournament.status !== 'ENDED' && (!latestPlayoffRound || (latestPlayoffRound.status === 'COMPLETED' && latestPlayoffRound.bracket_size > 2))" class="button primary" type="button" :disabled="busy" @click="generatePlayoffStage">生成下一阶段</button>
              <button v-if="latestPlayoffRound?.status === 'DRAFT'" class="button primary" type="button" :disabled="busy" @click="requestPlayoffStagePublish">正式发布{{ latestPlayoffRound.name }}</button>
              <button v-if="tournament.status === 'ELIMINATION' && playoff?.awaiting_tournament_end" class="button primary" type="button" :disabled="busy" @click="endTournament">结束赛事并锁定结果</button>
            </div>
          </div>
          <template v-if="playoff?.rounds.length">
            <nav class="competition-round-tabs" role="tablist" aria-label="淘汰赛阶段">
              <button v-for="round in playoff.rounds" :key="round.id" type="button" role="tab" :class="{ active: selectedPlayoffRound?.id === round.id }" :aria-selected="selectedPlayoffRound?.id === round.id" @click="selectedPlayoffRoundId = round.id">{{ round.name }}</button>
            </nav>
            <div v-if="selectedPlayoffRound" class="round-admin-heading">
              <div><strong>{{ selectedPlayoffRound.name }}</strong><span :class="['status-badge', `round-${selectedPlayoffRound.status.toLowerCase()}`]">{{ swissRoundStatusText[selectedPlayoffRound.status] }}</span></div>
              <label v-if="selectedPlayoffRound.status !== 'DRAFT'">筛选
                <select v-model="matchFilter"><option value="ALL">全部</option><option value="WAITING">未完成</option><option value="CONFLICT">赛果冲突</option><option value="COMPLETED">已完成</option></select>
              </label>
            </div>
            <div v-if="selectedPlayoffRound" class="admin-match-list playoff-match-list">
              <template v-for="match in filteredPlayoffMatches" :key="match.id">
                <article :class="['admin-match-row', { 'admin-match-row-preview': selectedPlayoffRound.status === 'DRAFT' }]">
                  <span class="match-table-no">第 {{ match.table_no }} 桌</span>
                  <div class="admin-match-players">
                    <span :class="['admin-match-player', 'admin-match-player-a', { winner: match.winner_id === match.player_a_id }]">
                      <strong>{{ match.player_a_nickname }}</strong><small v-if="displayedMatchResult(match, match.player_a_id)" :class="['admin-result-mark', `submission-${displayedMatchResult(match, match.player_a_id)?.toLowerCase()}`]">{{ displayedMatchResultText(match, match.player_a_id) }}</small><em>（#{{ match.seed_a }}）</em>
                    </span>
                    <i class="admin-match-versus">VS</i>
                    <span :class="['admin-match-player', 'admin-match-player-b', { winner: match.winner_id === match.player_b_id }]">
                      <small v-if="displayedMatchResult(match, match.player_b_id)" :class="['admin-result-mark', `submission-${displayedMatchResult(match, match.player_b_id)?.toLowerCase()}`]">{{ displayedMatchResultText(match, match.player_b_id) }}</small><strong>{{ match.player_b_nickname }}</strong><em>（#{{ match.seed_b }}）</em>
                    </span>
                  </div>
                  <div v-if="selectedPlayoffRound.status !== 'DRAFT'" class="admin-match-outcome">
                    <span :class="['status-badge', `match-${match.status.toLowerCase()}`]">{{ matchStatusText[match.status] }}</span>
                    <div v-if="!match.result_locked" class="row-actions"><button type="button" :aria-label="matchResolutionActionText(match)" :title="matchResolutionActionText(match)" :disabled="busy" @click="requestPlayoffResolution(match)">处理</button></div>
                  </div>
                </article>
                <section v-if="pendingPlayoffResolution?.match.id === match.id" class="forfeit-confirmation swiss-resolution-confirmation" role="dialog" :aria-labelledby="`playoff-resolution-title-${match.id}`">
                  <div class="match-resolution-toolbar">
                    <strong :id="`playoff-resolution-title-${match.id}`">{{ matchResolutionTitle(match) }}</strong>
                    <div class="match-resolution-winners">
                      <button :class="['button', 'small', pendingPlayoffResolution.winnerId === match.player_a_id ? 'primary' : 'secondary']" type="button" :disabled="busy" @click="pendingPlayoffResolution.winnerId = match.player_a_id">判 {{ match.player_a_nickname }} 胜</button>
                      <button :class="['button', 'small', pendingPlayoffResolution.winnerId === match.player_b_id ? 'primary' : 'secondary']" type="button" :disabled="busy" @click="pendingPlayoffResolution.winnerId = match.player_b_id">判 {{ match.player_b_nickname }} 胜</button>
                    </div>
                    <div class="form-actions swiss-resolution-actions"><button class="button secondary small" type="button" :disabled="busy" @click="cancelPlayoffResolution">取消</button><button class="button primary small" type="button" :disabled="busy || !canConfirmResolution(pendingPlayoffResolution)" @click="confirmPlayoffResolution">确认裁定</button></div>
                  </div>
                  <div class="match-resolution-meta">
                    <small class="match-resolution-summary">{{ pendingPlayoffResolution.winnerId ? resolutionSummary(match, pendingPlayoffResolution.winnerId) : '请选择获胜者' }}</small>
                    <button class="match-resolution-reason-toggle" type="button" :aria-expanded="pendingPlayoffResolution.reasonOpen" :aria-controls="`playoff-resolution-reason-${match.id}`" @click="pendingPlayoffResolution.reasonOpen = !pendingPlayoffResolution.reasonOpen">{{ pendingPlayoffResolution.reasonOpen ? '收起裁定原因' : '＋填写裁定原因（选填）' }}</button>
                  </div>
                  <label v-if="pendingPlayoffResolution.reasonOpen" :id="`playoff-resolution-reason-${match.id}`" class="match-resolution-reason"><span>裁定原因（选填）</span><input v-model.trim="pendingPlayoffResolution.reason" maxlength="500" placeholder="可不填" /></label>
                </section>
              </template>
              <p v-if="!filteredPlayoffMatches.length" class="empty-state compact">该筛选下没有对阵。</p>
            </div>
          </template>
          <p v-else class="empty-state">全部瑞士轮完成后，点击“生成下一阶段”创建 Top {{ tournament.playoff_size }} 固定种子对阵。</p>
        </template>
      </template>

      <template v-else-if="section === 'results' && competitionStage === 'swiss'">
        <section class="swiss-ranking-section">
          <div class="ranking-heading"><h3>瑞士轮排名</h3><span>第 {{ swissOverview?.ranking_round_no ?? 0 }} 轮快照</span></div>
          <div class="ranking-table-wrap">
            <table class="ranking-table">
              <thead><tr><th>排名</th><th>选手</th><th>胜负</th><th>OMW(%)</th><th>LRS</th></tr></thead>
              <tbody>
                <template v-for="item in swissOverview?.rankings" :key="item.participant_id">
                  <tr :class="{ 'ranking-row-selected': selectedRankingParticipantId === item.participant_id }">
                    <td>{{ item.rank }}</td>
                    <td><button class="ranking-player-button" type="button" :aria-expanded="selectedRankingParticipantId === item.participant_id" :aria-controls="`ranking-history-${item.participant_id}`" @click="toggleRankingHistory(item.participant_id)">{{ item.nickname }}<small v-if="item.participant_status === 'WITHDRAWN'">已退赛</small></button></td>
                    <td>{{ item.wins }}-{{ item.losses }}</td><td>{{ (item.omw * 100).toFixed(2) }}</td><td>{{ item.loss_round_score }}</td>
                  </tr>
                  <tr v-if="selectedRankingParticipantId === item.participant_id" class="ranking-history-row"><td colspan="5"><div :id="`ranking-history-${item.participant_id}`" class="ranking-player-history"><MatchHistoryList :matches="selectedRankingHistory" :title="`${item.nickname}的历史对阵`" /></div></td></tr>
                </template>
                <tr v-if="!swissOverview?.rankings.length"><td colspan="5">尚无瑞士轮排名。</td></tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>

      <PlayoffResultsTree v-else :overview="playoff" />
    </section>

    <section v-if="tournament && section === 'decks-report'" class="phase5-admin">
      <div v-if="tournament.status !== 'ENDED'" class="empty-state">赛事结束后开放四强卡组审核与周报发布。</div>
      <template v-else>
        <div class="swiss-operation-bar"><div><h2>四强卡组截图</h2><p>截图审核通过后即锁定；4/4 全部通过才允许生成周报。</p></div><strong>{{ deckSubmissions?.approved_count ?? 0 }} / 4 已通过</strong></div>
        <div class="deck-review-grid">
          <article v-for="item in deckSubmissions?.items" :key="item.id" class="deck-review-card">
            <header><span>{{ deckPlacementText(item.placement) }}</span><strong>{{ item.nickname }}</strong><i :class="['status-badge', `deck-${item.status.toLowerCase()}`]">{{ deckStatusText[item.status] }}</i></header>
            <img v-if="item.image_url" :src="item.image_url" :alt="`${item.nickname} 的卡组截图`" />
            <div v-else class="deck-image-empty">等待选手上传</div>
            <footer v-if="item.status === 'PENDING_REVIEW'" class="row-actions"><button type="button" :disabled="busy || !item.image_url" @click="openDeckPreview(item)">预览</button><button type="button" :disabled="busy" @click="reviewDeck(item, 'approve')">审核通过</button><button type="button" :disabled="busy" @click="reviewDeck(item, 'return')">退回重传</button></footer>
          </article>
        </div>

        <div class="report-admin-heading"><div><p class="section-kicker">WEEKLY REPORT</p><h2>赛事周报</h2><p>四强截图全部审核通过后，一键生成并发布固定模板周报；当前不提供编辑或预览。</p></div><div class="form-actions"><button v-if="weeklyReport?.status !== 'PUBLISHED'" class="button primary" type="button" :disabled="busy || deckSubmissions?.approved_count !== 4" @click="generateWeeklyReport">生成周报</button><RouterLink v-if="weeklyReport?.status === 'PUBLISHED'" class="button secondary" :to="`/reports/${weeklyReport.id}`">查看已发布周报</RouterLink></div></div>
        <p v-if="weeklyReport?.status !== 'PUBLISHED'" class="empty-state compact">四强截图 4/4 审核通过后可直接生成正式周报。</p>
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
        <article v-for="item in auditLogs.items" :key="item.id" class="audit-row"><time>{{ formatAuditTime(item.created_at) }}</time><div><strong>{{ auditActionText(item.action_type) }}</strong><p>{{ item.operator_nickname }} · {{ item.target_type }} / {{ item.target_id }}</p></div><details><summary>数据变化</summary><pre>{{ JSON.stringify({ before: item.before_json, after: item.after_json }, null, 2) }}</pre></details></article>
      </div>
      <p v-else class="empty-state">尚无本届赛事审计记录。</p>
    </section>
  </div>
</template>
