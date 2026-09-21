<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { apiGet } from '@/api/client'
import FormMessage from '@/components/FormMessage.vue'
import { useLiveRefresh } from '@/composables/useLiveRefresh'
import { useAuthStore } from '@/stores/auth'
import type { QqOAuthStatus } from '@/types/auth'
import type { PlayerStatistics } from '@/types/statistics'
import { finishLevelText } from '@/types/statistics'

const authStore = useAuthStore()
const route = useRoute()
const form = reactive({ current: '', next: '', confirm: '' })
const message = ref('')
const error = ref('')
const qqStatus = ref<QqOAuthStatus | null>(null)
const passwordFormOpen = ref(false)
const activeSection = ref<'account' | 'records'>(route.query.section === 'records' ? 'records' : 'account')
const statistics = ref<PlayerStatistics | null>(null)
const statisticsError = ref('')
const loadingMoreResults = ref(false)
const loadMoreResultsError = ref('')

async function loadStatistics(append = false, limit = 10) {
  if (!authStore.token) return
  const offset = append ? statistics.value?.results.length ?? 0 : 0
  const response = await apiGet<PlayerStatistics>(
    `/me/tournament-statistics?offset=${offset}&limit=${limit}`, undefined, authStore.token,
  )
  statistics.value = append && statistics.value
    ? { ...response, results: [...statistics.value.results, ...response.results] }
    : response
}

async function loadMoreResults() {
  loadingMoreResults.value = true
  loadMoreResultsError.value = ''
  try {
    await loadStatistics(true)
  } catch (caught) {
    loadMoreResultsError.value = caught instanceof Error ? caught.message : '更多历届成绩加载失败'
  } finally {
    loadingMoreResults.value = false
  }
}

async function refreshProfileData(): Promise<void> {
  if (authStore.token && activeSection.value === 'records') {
    await loadStatistics(false, Math.min(100, Math.max(10, statistics.value?.results.length ?? 0))).catch((caught: unknown) => {
      statisticsError.value = caught instanceof Error ? caught.message : '赛事档案刷新失败'
    })
  }
  qqStatus.value = await apiGet<QqOAuthStatus>('/auth/qq/status').catch(() => null)
}

watch(activeSection, () => {
  void refreshProfileData()
})
useLiveRefresh(refreshProfileData)

onMounted(async () => {
  if (authStore.token) {
    await loadStatistics().catch((caught: unknown) => {
      statisticsError.value = caught instanceof Error ? caught.message : '赛事档案加载失败'
    })
  }
  qqStatus.value = await apiGet<QqOAuthStatus>('/auth/qq/status').catch(() => null)
  const pendingBinding = sessionStorage.getItem('lizibei_qq_binding_token')
  if (pendingBinding) {
    try {
      await authStore.bindQq(pendingBinding)
      sessionStorage.removeItem('lizibei_qq_binding_token')
      message.value = 'QQ 授权已绑定。'
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'QQ 绑定失败'
    }
  }
})

async function changePassword() {
  message.value = ''
  error.value = ''
  try {
    await authStore.changePassword(form.current, form.next, form.confirm)
    form.current = ''
    form.next = ''
    form.confirm = ''
    message.value = '密码已更新。'
    passwordFormOpen.value = false
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '密码修改失败'
  }
}

function openPasswordForm() {
  message.value = ''
  error.value = ''
  passwordFormOpen.value = true
}

function closePasswordForm() {
  form.current = ''
  form.next = ''
  form.confirm = ''
  error.value = ''
  passwordFormOpen.value = false
}
</script>

<template>
  <div class="page-shell account-page">
    <header class="page-heading">
      <h1>个人中心</h1>
      <p>账号资料、登录安全与个人赛事表现。</p>
    </header>
    <nav class="account-section-nav" aria-label="个人中心栏目">
      <button type="button" :class="{ active: activeSection === 'account' }" :aria-current="activeSection === 'account' ? 'page' : undefined" @click="activeSection = 'account'">账号资料</button>
      <button type="button" :class="{ active: activeSection === 'records' }" :aria-current="activeSection === 'records' ? 'page' : undefined" @click="activeSection = 'records'">赛事档案</button>
    </nav>
    <FormMessage v-if="activeSection === 'account' && message" type="success" :message="message" />
    <FormMessage v-if="activeSection === 'account' && error && !passwordFormOpen" :message="error" />
    <div v-if="authStore.user && activeSection === 'account'" :class="['account-layout', { 'password-form-open': passwordFormOpen }]">
      <section class="profile-details">
        <h2>账号资料</h2>
        <dl class="definition-list">
          <div><dt>昵称</dt><dd>{{ authStore.user.nickname }}</dd></div>
          <div v-if="authStore.user.phone_number"><dt>手机号</dt><dd>{{ authStore.user.phone_number }}</dd></div>
          <div v-if="authStore.user.qq_number"><dt>QQ 号</dt><dd>{{ authStore.user.qq_number }}</dd></div>
          <div><dt>全局角色</dt><dd>{{ authStore.isPlatformAdmin ? '平台管理员' : '用户' }}</dd></div>
          <div><dt>QQ 授权</dt><dd>{{ authStore.user.qq_bound ? '已绑定' : '未绑定' }}</dd></div>
        </dl>
        <p class="form-hint">登录账号和昵称当前不可修改。</p>
        <a v-if="!authStore.user.qq_bound && qqStatus?.configured" class="button secondary qq-bind-button" :href="qqStatus.authorization_url ?? '#'">绑定 QQ 授权</a>
        <section class="security-settings" aria-labelledby="security-settings-title">
          <div>
            <h2 id="security-settings-title">账号安全</h2>
            <p>定期更新登录密码可以提高账号安全性。</p>
          </div>
          <button
            class="button secondary"
            type="button"
            aria-controls="password-settings-form"
            :aria-expanded="passwordFormOpen"
            @click="openPasswordForm"
          >修改密码</button>
        </section>
      </section>
      <form
        v-if="passwordFormOpen"
        id="password-settings-form"
        class="settings-form"
        @submit.prevent="changePassword"
      >
        <h2>修改密码</h2>
        <FormMessage v-if="error" :message="error" />
        <label><span>当前密码</span><input v-model="form.current" type="password" autocomplete="current-password" required /></label>
        <label><span>新密码</span><input v-model="form.next" type="password" minlength="6" autocomplete="new-password" required /></label>
        <label><span>确认新密码</span><input v-model="form.confirm" type="password" minlength="6" autocomplete="new-password" required /></label>
        <div class="form-actions password-form-actions">
          <button class="button primary" type="submit">保存新密码</button>
          <button class="button secondary" type="button" @click="closePasswordForm">取消</button>
        </div>
      </form>
    </div>
    <section v-else-if="authStore.user" class="competition-records" aria-labelledby="competition-records-title">
      <FormMessage v-if="statisticsError" :message="statisticsError" />
      <template v-if="statistics">
        <div class="record-section-heading">
          <div>
            <h2 id="competition-records-title">赛事档案</h2>
          </div>
          <p>仅统计已结束并锁定结果的赛事。</p>
        </div>
        <dl class="record-statistics">
          <div class="record-statistics-primary"><dt>比赛积分</dt><dd>{{ statistics.total_points }}</dd></div>
          <div><dt>参赛次数</dt><dd>{{ statistics.tournament_count }}</dd></div>
          <div><dt>冠军</dt><dd>{{ statistics.champion_count }}</dd></div>
          <div><dt>亚军</dt><dd>{{ statistics.runner_up_count }}</dd></div>
          <div><dt>晋级四强</dt><dd>{{ statistics.top_4_count }}</dd></div>
          <div><dt>晋级八强</dt><dd>{{ statistics.top_8_count }}</dd></div>
        </dl>
        <section class="record-history" aria-labelledby="record-history-title">
          <div class="record-history-heading">
            <h2 id="record-history-title">历届成绩</h2>
            <span>共 {{ statistics.tournament_count }} 届</span>
          </div>
          <div v-if="statistics.results.length" class="record-history-table-wrap">
            <table class="record-history-table">
              <thead><tr><th>赛事</th><th>最终成绩</th><th>瑞士轮排名</th><th>战绩</th><th>积分</th></tr></thead>
              <tbody>
                <tr v-for="item in statistics.results" :key="item.tournament_id">
                  <td><RouterLink :to="{ path: `/tournaments/${item.tournament_id}`, query: { from: 'records' } }">{{ item.tournament_name }}</RouterLink><small v-if="item.participant_status === 'WITHDRAWN'">已退赛</small></td>
                  <td data-label="最终成绩"><strong>{{ finishLevelText[item.finish_level] }}</strong></td>
                  <td data-label="瑞士排名">{{ item.swiss_rank ? `第 ${item.swiss_rank} 名` : '—' }}</td>
                  <td data-label="战绩"><span>{{ item.wins }}-{{ item.losses }}<small v-if="item.bye_count">{{ item.bye_count }} 次轮空</small></span></td>
                  <td data-label="积分"><strong>+{{ item.points_awarded }}</strong></td>
                </tr>
              </tbody>
            </table>
            <div v-if="statistics.results.length < statistics.tournament_count" class="form-actions tournament-load-more"><button class="button secondary" type="button" :disabled="loadingMoreResults" @click="loadMoreResults">{{ loadingMoreResults ? '加载中…' : '加载更多' }}</button></div>
            <FormMessage v-if="loadMoreResultsError" :message="loadMoreResultsError" />
          </div>
          <p v-else class="empty-state compact">还没有已结算的赛事记录。</p>
        </section>
      </template>
    </section>
  </div>
</template>
