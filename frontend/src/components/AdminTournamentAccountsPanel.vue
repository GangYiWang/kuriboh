<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { ApiError, apiGet, apiPost, apiPostForm } from '@/api/client'
import ConfirmFormDialog from '@/components/ConfirmFormDialog.vue'
import FormMessage from '@/components/FormMessage.vue'
import { useLiveRefresh } from '@/composables/useLiveRefresh'
import type {
  AccountImportResponse,
  AccountCarryoverSummary,
  AccountInventorySummary,
  AccountReplacementStatus,
  AccountType,
  AdminAccountReplacementRequest,
  AdminAccountReplacementRequestListResponse,
  AdminTournamentAccountListResponse,
  TournamentAccountStatus,
  TournamentStatus,
} from '@/types/tournament'

interface ImportErrorDetail {
  line: number
  reason: string
}

type AccountAdminView = 'inventory' | 'replacements'
type ReplacementReviewAction = 'approve' | 'reject'

const props = defineProps<{
  tournamentId: string
  token: string
  tournamentStatus: TournamentStatus
}>()

const accountTypes: AccountType[] = ['KONAMI', 'STEAM']
const activeView = ref<AccountAdminView>('inventory')
const activeType = ref<AccountType>('KONAMI')
const inventory = ref<AdminTournamentAccountListResponse | null>(null)
const replacements = ref<AdminAccountReplacementRequestListResponse | null>(null)
const carryoverPreview = ref<AccountCarryoverSummary | null>(null)
const carryoverOpen = ref(false)
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const reviewRequest = ref<AdminAccountReplacementRequest | null>(null)
const reviewAction = ref<ReplacementReviewAction | null>(null)
const reviewReason = ref('')
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const message = ref('')
const importErrors = ref<ImportErrorDetail[]>([])
const importOpen = computed(() => !['ENDED', 'CANCELED'].includes(props.tournamentStatus))
const carryoverAllowed = computed(() => ['DRAFT', 'REGISTRATION'].includes(props.tournamentStatus))
const summary = computed<AccountInventorySummary>(() => inventory.value?.summaries.find(
  (item) => item.account_type === activeType.value,
) ?? {
  account_type: activeType.value,
  total: 0,
  available: 0,
  reserved: 0,
  claimed: 0,
  invalid: 0,
  transferred: 0,
})
const carryoverDescription = computed(() => {
  const preview = carryoverPreview.value
  if (!preview) return ''
  const counts = [
    preview.konami_count ? `科乐美账号 ${preview.konami_count} 个` : '',
    preview.steam_count ? `Steam 账号 ${preview.steam_count} 个` : '',
  ].filter(Boolean).join('，')
  return `确认将 ${preview.source_tournament_count} 届往届赛事的未使用账号结转到当前赛事？共 ${preview.total_count} 个：${counts}。已领取、已预留和已作废账号不会结转。`
})

const typeText: Record<AccountType, string> = {
  KONAMI: '科乐美账号',
  STEAM: 'Steam 账号',
}

const accountStatusText: Record<TournamentAccountStatus, string> = {
  AVAILABLE: '可领取',
  RESERVED: '待重新获取',
  CLAIMED: '已领取',
  INVALID: '已作废',
  TRANSFERRED: '已结转',
}

const replacementStatusText: Record<AccountReplacementStatus, string> = {
  PENDING: '待审核',
  APPROVED: '待选手获取',
  COMPLETED: '已完成',
  REJECTED: '已拒绝',
}

function formatTime(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
    : '—'
}

function parseImportErrors(details: unknown): ImportErrorDetail[] {
  if (!details || typeof details !== 'object' || !('errors' in details) || !Array.isArray(details.errors)) return []
  return details.errors.filter((item): item is ImportErrorDetail => Boolean(
    item && typeof item === 'object' && 'line' in item && typeof item.line === 'number'
      && 'reason' in item && typeof item.reason === 'string',
  ))
}

async function loadInventory(): Promise<void> {
  inventory.value = await apiGet<AdminTournamentAccountListResponse>(
    `/admin/tournaments/${props.tournamentId}/accounts?type=${activeType.value}`,
    undefined,
    props.token,
  )
}

async function loadReplacements(): Promise<void> {
  replacements.value = await apiGet<AdminAccountReplacementRequestListResponse>(
    `/admin/tournaments/${props.tournamentId}/account-replacement-requests`,
    undefined,
    props.token,
  )
}

async function loadCarryoverPreview(): Promise<void> {
  if (!carryoverAllowed.value) {
    carryoverPreview.value = null
    return
  }
  carryoverPreview.value = await apiGet<AccountCarryoverSummary>(
    `/admin/tournaments/${props.tournamentId}/accounts/carryover-preview`,
    undefined,
    props.token,
  )
}

async function refreshAccounts(): Promise<void> {
  try {
    await Promise.all([loadInventory(), loadReplacements(), loadCarryoverPreview()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '账号分发数据刷新失败'
  }
}

function openCarryover(): void {
  error.value = ''
  message.value = ''
  carryoverOpen.value = true
}

function closeCarryover(): void {
  carryoverOpen.value = false
  error.value = ''
}

async function carryoverAccounts(): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    const result = await apiPost<AccountCarryoverSummary>(
      `/admin/tournaments/${props.tournamentId}/accounts/carryover`,
      {},
      props.token,
    )
    message.value = `已结转 ${result.total_count} 个往届余号：科乐美 ${result.konami_count} 个，Steam ${result.steam_count} 个。`
    carryoverOpen.value = false
    await Promise.all([loadInventory(), loadCarryoverPreview()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '余号结转失败'
  } finally {
    busy.value = false
  }
}

function chooseFile(event: Event): void {
  const target = event.target as HTMLInputElement
  selectedFile.value = target.files?.[0] ?? null
  error.value = ''
  importErrors.value = []
}

async function importAccounts(): Promise<void> {
  if (!selectedFile.value) {
    error.value = '请先选择账号文本文件。'
    return
  }
  busy.value = true
  error.value = ''
  message.value = ''
  importErrors.value = []
  try {
    const form = new FormData()
    form.append('file', selectedFile.value)
    const result = await apiPostForm<AccountImportResponse>(
      `/admin/tournaments/${props.tournamentId}/accounts/${activeType.value}/imports`,
      form,
      props.token,
    )
    message.value = `成功导入 ${result.imported_count} 个${typeText[activeType.value]}，当前可用 ${result.available_count} 个。`
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
    await loadInventory()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '账号文件导入失败'
    if (caught instanceof ApiError) importErrors.value = parseImportErrors(caught.body.details)
  } finally {
    busy.value = false
  }
}

function openReview(item: AdminAccountReplacementRequest, action: ReplacementReviewAction): void {
  reviewRequest.value = item
  reviewAction.value = action
  reviewReason.value = ''
  error.value = ''
  message.value = ''
}

function closeReview(): void {
  reviewRequest.value = null
  reviewAction.value = null
  reviewReason.value = ''
  error.value = ''
}

async function submitReview(): Promise<void> {
  if (!reviewRequest.value || !reviewAction.value) return
  if (reviewAction.value === 'reject' && !reviewReason.value.trim()) return
  const action = reviewAction.value
  busy.value = true
  error.value = ''
  try {
    await apiPost<AdminAccountReplacementRequest>(
      `/admin/tournaments/${props.tournamentId}/account-replacement-requests/${reviewRequest.value.id}/${action}`,
      action === 'reject' ? { reason: reviewReason.value } : {},
      props.token,
    )
    message.value = action === 'approve' ? '换号申请已通过，新账号已为选手预留。' : '换号申请已拒绝。'
    reviewRequest.value = null
    reviewAction.value = null
    reviewReason.value = ''
    await Promise.all([loadReplacements(), loadInventory()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '换号申请处理失败'
  } finally {
    busy.value = false
  }
}

watch(activeType, async () => {
  selectedFile.value = null
  error.value = ''
  message.value = ''
  importErrors.value = []
  if (fileInput.value) fileInput.value.value = ''
  loading.value = true
  try {
    await loadInventory()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '账号库存加载失败'
  } finally {
    loading.value = false
  }
})

onMounted(async () => {
  try {
    await Promise.all([loadInventory(), loadReplacements(), loadCarryoverPreview()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '账号分发数据加载失败'
  } finally {
    loading.value = false
  }
})
watch(() => [props.tournamentId, props.tournamentStatus], () => {
  void refreshAccounts()
})
useLiveRefresh(refreshAccounts)
</script>

<template>
  <section class="account-admin" aria-labelledby="account-admin-title">
    <header class="settings-heading">
      <div><h2 id="account-admin-title">账号分发</h2><p>导入本场赛事的账号库存，并处理选手的换号申请。密码不会显示在管理列表中。</p></div>
    </header>
    <nav class="player-tabs" role="tablist" aria-label="账号分发内容">
      <button type="button" role="tab" :class="{ active: activeView === 'inventory' }" :aria-selected="activeView === 'inventory'" @click="activeView = 'inventory'">账号库存</button>
      <button type="button" role="tab" :class="{ active: activeView === 'replacements' }" :aria-selected="activeView === 'replacements'" @click="activeView = 'replacements'">换号申请 <small v-if="(replacements?.pending_count ?? 0) > 0" class="replacement-request-count">{{ replacements?.pending_count }}</small></button>
    </nav>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />

    <div v-if="activeView === 'inventory'" role="tabpanel">
      <div v-if="(carryoverPreview?.total_count ?? 0) > 0" class="account-carryover-bar">
        <div>
          <strong>往届可结转</strong>
          <p>科乐美 {{ carryoverPreview?.konami_count ?? 0 }} 个 · Steam {{ carryoverPreview?.steam_count ?? 0 }} 个</p>
        </div>
        <button class="button secondary small" type="button" :disabled="busy" @click="openCarryover">结转余号</button>
      </div>
      <nav class="account-type-tabs" role="tablist" aria-label="账号类型">
        <button v-for="accountType in accountTypes" :key="accountType" type="button" role="tab" :class="{ active: activeType === accountType }" :aria-selected="activeType === accountType" @click="activeType = accountType">{{ typeText[accountType] }}</button>
      </nav>
      <ul v-if="importErrors.length" class="account-import-errors">
        <li v-for="item in importErrors" :key="`${item.line}-${item.reason}`">第 {{ item.line }} 行：{{ item.reason }}</li>
      </ul>
      <div class="account-import-bar">
        <div>
          <strong>导入{{ typeText[activeType] }}</strong>
          <p>每个非空行使用 <code>账号----密码</code> 格式；账号去重区分大小写。</p>
        </div>
        <div v-if="importOpen" class="account-import-actions">
          <label class="file-control"><span>选择 .txt 文件</span><input ref="fileInput" type="file" accept=".txt,text/plain" :disabled="busy" @change="chooseFile" /></label>
          <button class="button primary small" type="button" :disabled="busy || !selectedFile" @click="importAccounts">{{ busy ? '正在导入…' : '导入账号' }}</button>
        </div>
        <p v-else class="form-hint">赛事已经结束或取消，账号库存仅供查看。</p>
      </div>
      <dl class="player-summary" aria-label="账号库存概览">
        <div><dt>库存总数</dt><dd>{{ summary.total }}</dd></div>
        <div><dt>可领取</dt><dd>{{ summary.available }}</dd></div>
        <div><dt>待重新获取</dt><dd>{{ summary.reserved }}</dd></div>
        <div><dt>已领取</dt><dd>{{ summary.claimed }}</dd></div>
        <div><dt>已作废</dt><dd>{{ summary.invalid }}</dd></div>
        <div><dt>已结转</dt><dd>{{ summary.transferred }}</dd></div>
      </dl>
      <p v-if="loading" class="empty-state">正在加载账号库存…</p>
      <p v-else-if="!inventory?.items.length" class="empty-state">尚未导入{{ typeText[activeType] }}。</p>
      <div v-else class="player-table-wrap account-inventory-table">
        <table class="player-table">
          <thead><tr><th>账号</th><th>状态</th><th>领取选手</th><th>领取时间</th></tr></thead>
          <tbody>
            <tr v-for="item in inventory.items" :key="item.id">
              <td><code>{{ item.account }}</code></td>
              <td><span :class="['status-badge', `account-${item.status.toLowerCase()}`]">{{ accountStatusText[item.status] }}</span></td>
              <td>{{ item.claimed_by_nickname ?? '—' }}</td>
              <td><time>{{ formatTime(item.claimed_at) }}</time></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else role="tabpanel" class="account-replacement-admin">
      <p v-if="loading" class="empty-state">正在加载换号申请…</p>
      <p v-else-if="!replacements?.items.length" class="empty-state">暂无换号申请。</p>
      <div v-else class="player-table-wrap">
        <table class="player-table account-replacement-table">
          <thead><tr><th>选手</th><th>账号</th><th>申请原因</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="item in replacements.items" :key="item.id">
              <td><strong>{{ item.nickname }}</strong><small>{{ formatTime(item.created_at) }}</small></td>
              <td><span>{{ typeText[item.account_type] }}</span><code>{{ item.original_account }}</code></td>
              <td><p>{{ item.reason }}</p><small v-if="item.rejection_reason">拒绝原因：{{ item.rejection_reason }}</small></td>
              <td><span :class="['status-badge', `replacement-${item.status.toLowerCase()}`]">{{ replacementStatusText[item.status] }}</span><small v-if="item.replacement_account">新账号：{{ item.replacement_account }}</small></td>
              <td>
                <div v-if="item.status === 'PENDING'" class="row-actions">
                  <button type="button" :disabled="busy" @click="openReview(item, 'approve')">通过</button>
                  <button type="button" :disabled="busy" @click="openReview(item, 'reject')">拒绝</button>
                </div>
                <span v-else class="table-placeholder">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ConfirmFormDialog
      v-if="carryoverOpen"
      title="结转余号"
      :description="carryoverDescription"
      confirm-text="确认结转"
      :busy="busy"
      :error="error"
      @cancel="closeCarryover"
      @confirm="carryoverAccounts"
    />
    <ConfirmFormDialog
      v-if="reviewRequest && reviewAction"
      v-model:reason="reviewReason"
      :title="reviewAction === 'approve' ? '通过换号申请' : '拒绝换号申请'"
      :description="reviewAction === 'approve' ? `确认将 ${reviewRequest.nickname} 的原账号标记为已作废，并为其预留一个新的${typeText[reviewRequest.account_type]}？` : `请填写拒绝 ${reviewRequest.nickname} 换号申请的原因。`"
      :confirm-text="reviewAction === 'approve' ? '确认通过' : '确认拒绝'"
      :reason-label="reviewAction === 'reject' ? '拒绝原因（必填）' : undefined"
      reason-placeholder="请填写拒绝原因"
      :reason-required="reviewAction === 'reject'"
      :busy="busy"
      :error="error"
      @cancel="closeReview"
      @confirm="submitReview"
    />
  </section>
</template>
