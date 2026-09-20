<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { apiGet, apiPost } from '@/api/client'
import ConfirmFormDialog from '@/components/ConfirmFormDialog.vue'
import FormMessage from '@/components/FormMessage.vue'
import type {
  AccountCredential,
  AccountReplacementRequest,
  AccountType,
  MyTournamentAccountsResponse,
  RegistrationStatus,
  TournamentStatus,
} from '@/types/tournament'
import { copyText } from '@/utils/clipboard'

const props = defineProps<{
  tournamentId: string
  token: string
  tournamentStatus: TournamentStatus
  registrationStatus: RegistrationStatus
}>()

const accountTypes: AccountType[] = ['KONAMI', 'STEAM']
const accounts = ref<AccountCredential[]>([])
const replacementRequests = ref<AccountReplacementRequest[]>([])
const pendingType = ref<AccountType | null>(null)
const replacementType = ref<AccountType | null>(null)
const replacementReason = ref('')
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const message = ref('')
const claimOpen = computed(() => props.registrationStatus === 'APPROVED'
  && ['REGISTRATION', 'SWISS', 'ELIMINATION'].includes(props.tournamentStatus))
const byType = computed(() => new Map(accounts.value.map((item) => [item.account_type, item])))
const requestByType = computed(() => new Map(
  replacementRequests.value.map((item) => [item.account_type, item]),
))
const isReplacementClaim = computed(() => pendingType.value !== null
  && requestByType.value.get(pendingType.value)?.status === 'APPROVED')

const typeText: Record<AccountType, string> = {
  KONAMI: '科乐美账号',
  STEAM: 'Steam 账号',
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function canRequestReplacement(accountType: AccountType): boolean {
  const status = requestByType.value.get(accountType)?.status
  return claimOpen.value && !['PENDING', 'APPROVED'].includes(status ?? '')
}

async function loadAccounts(): Promise<void> {
  const response = await apiGet<MyTournamentAccountsResponse>(
    `/tournaments/${props.tournamentId}/accounts/me`, undefined, props.token,
  )
  accounts.value = response.items
  replacementRequests.value = response.replacement_requests
}

function requestClaim(accountType: AccountType): void {
  error.value = ''
  message.value = ''
  pendingType.value = accountType
}

async function claim(): Promise<void> {
  if (!pendingType.value) return
  const accountType = pendingType.value
  const replacement = isReplacementClaim.value
  busy.value = true
  error.value = ''
  try {
    await apiPost<AccountCredential>(
      `/tournaments/${props.tournamentId}/accounts/${accountType}/claim`, {}, props.token,
    )
    await loadAccounts()
    message.value = `${typeText[accountType]}${replacement ? '重新获取' : '领取'}成功。`
    pendingType.value = null
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事账号领取失败'
    await loadAccounts().catch(() => undefined)
    if (byType.value.has(accountType)) pendingType.value = null
  } finally {
    busy.value = false
  }
}

function openReplacementRequest(accountType: AccountType): void {
  replacementType.value = accountType
  replacementReason.value = ''
  error.value = ''
  message.value = ''
}

function closeReplacementRequest(): void {
  replacementType.value = null
  replacementReason.value = ''
  error.value = ''
}

async function submitReplacementRequest(): Promise<void> {
  if (!replacementType.value || !replacementReason.value.trim()) return
  const accountType = replacementType.value
  busy.value = true
  error.value = ''
  try {
    const request = await apiPost<AccountReplacementRequest>(
      `/tournaments/${props.tournamentId}/accounts/${accountType}/replacement-requests`,
      { reason: replacementReason.value },
      props.token,
    )
    replacementRequests.value = [
      ...replacementRequests.value.filter((item) => item.account_type !== accountType),
      request,
    ]
    message.value = `${typeText[accountType]}换号申请已提交。`
    replacementType.value = null
    replacementReason.value = ''
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '换号申请提交失败'
  } finally {
    busy.value = false
  }
}

async function copyValue(value: string, label: string): Promise<void> {
  try {
    await copyText(value)
    message.value = `${label}已复制。`
    error.value = ''
  } catch {
    error.value = '复制失败，请手动选择并复制。'
  }
}

onMounted(async () => {
  try {
    await loadAccounts()
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '赛事账号加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="tournament-accounts-panel" aria-labelledby="tournament-accounts-title">
    <header class="section-title-row">
      <div>
        <h2 id="tournament-accounts-title">赛事账号</h2>
        <p>每种账号只能领取一次，领取后可在本页继续查看。</p>
      </div>
    </header>
    <FormMessage v-if="message" type="success" :message="message" />
    <FormMessage v-if="error" :message="error" />
    <p v-if="loading" class="empty-state compact">正在加载赛事账号…</p>
    <div v-else class="account-claim-list">
      <article v-for="accountType in accountTypes" :key="accountType" class="account-claim-row">
        <div class="account-claim-heading">
          <div>
            <h3>{{ typeText[accountType] }}</h3>
            <p>{{ accountType === 'STEAM' ? '仅在确实需要时领取，领取后将占用一个赛事库存账号。' : '报名审核通过后可领取本场赛事使用的科乐美账号。' }}</p>
          </div>
          <span v-if="byType.has(accountType)" class="status-badge account-claimed">已领取</span>
          <span v-else-if="requestByType.get(accountType)?.status === 'APPROVED'" class="status-badge account-reserved">换号已通过</span>
        </div>
        <dl v-if="byType.get(accountType)" class="account-credential-list">
          <div>
            <dt>账号</dt>
            <dd><code>{{ byType.get(accountType)?.account }}</code><button type="button" class="text-action" @click="copyValue(byType.get(accountType)?.account ?? '', '账号')">复制</button></dd>
          </div>
          <div>
            <dt>密码</dt>
            <dd><code>{{ byType.get(accountType)?.password }}</code><button type="button" class="text-action" @click="copyValue(byType.get(accountType)?.password ?? '', '密码')">复制</button></dd>
          </div>
          <div><dt>领取时间</dt><dd>{{ formatTime(byType.get(accountType)?.claimed_at ?? '') }}</dd></div>
        </dl>
        <div v-if="requestByType.get(accountType)?.status === 'PENDING'" class="account-replacement-state">
          <strong>换号申请待审核</strong>
          <p>申请原因：{{ requestByType.get(accountType)?.reason }}</p>
        </div>
        <div v-else-if="requestByType.get(accountType)?.status === 'REJECTED'" class="account-replacement-state rejected">
          <strong>换号申请已拒绝</strong>
          <p>拒绝原因：{{ requestByType.get(accountType)?.rejection_reason }}</p>
        </div>
        <div v-if="byType.get(accountType)" class="account-replacement-action">
          <button
            v-if="canRequestReplacement(accountType)"
            class="button secondary small"
            type="button"
            :disabled="busy"
            @click="openReplacementRequest(accountType)"
          >{{ requestByType.get(accountType)?.status === 'REJECTED' ? '重新申请换号' : '申请换号' }}</button>
        </div>
        <div v-else class="account-claim-action">
          <p v-if="!claimOpen">当前报名或赛事状态不可领取账号。</p>
          <button
            v-else-if="requestByType.get(accountType)?.status === 'APPROVED'"
            class="button primary"
            type="button"
            :disabled="busy"
            @click="requestClaim(accountType)"
          >重新获取{{ typeText[accountType] }}</button>
          <button v-else class="button primary" type="button" :disabled="busy" @click="requestClaim(accountType)">领取{{ typeText[accountType] }}</button>
        </div>
      </article>
    </div>
    <ConfirmFormDialog
      v-if="pendingType"
      :title="`${isReplacementClaim ? '重新获取' : '领取'}${typeText[pendingType]}`"
      :description="isReplacementClaim ? '换号申请已通过，确认获取为你预留的新账号。' : pendingType === 'STEAM' ? '每位选手只能领取一个 Steam 账号。请确认你确实需要使用后再领取。' : '每位选手只能领取一个科乐美账号，领取后不能再次领取其他账号。'"
      confirm-text="确认领取"
      :busy="busy"
      :error="error"
      @cancel="pendingType = null"
      @confirm="claim"
    />
    <ConfirmFormDialog
      v-if="replacementType"
      v-model:reason="replacementReason"
      :title="`申请更换${typeText[replacementType]}`"
      description="请说明当前账号遇到的问题。申请提交后，由赛事主办方人工检查并处理。"
      confirm-text="确认申请"
      reason-label="换号原因（必填）"
      reason-placeholder="请填写账号无法使用的具体情况"
      :reason-maxlength="500"
      reason-required
      :busy="busy"
      :error="error"
      @cancel="closeReplacementRequest"
      @confirm="submitReplacementRequest"
    />
  </section>
</template>
