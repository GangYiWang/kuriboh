<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import FormMessage from '@/components/FormMessage.vue'
import {
  calculateSwissCut,
  type SwissCutGroup,
  type SwissCutResult,
} from '@/utils/swissCutCalculator'

const form = reactive({
  playerCount: 27,
  roundCount: 4,
  topCut: 8,
})
const result = ref<SwissCutResult | null>(null)
const error = ref('')

const maximumRisk = computed(() => {
  if (!result.value) return null
  let risk: { record: string; misses: number } | null = null
  for (const group of result.value.groups) {
    for (const scenario of group.scenarios) {
      const misses = scenario.boundaryPlayerCount - scenario.boundaryQualifiers
      if (!risk || misses > risk.misses) risk = { record: group.boundaryRecord, misses }
    }
  }
  return risk
})

function calculate(): void {
  error.value = ''
  try {
    result.value = calculateSwissCut({
      playerCount: form.playerCount,
      roundCount: form.roundCount,
      topCut: form.topCut,
    })
  } catch (caught) {
    result.value = null
    error.value = caught instanceof Error ? caught.message : '计算失败，请检查输入'
  }
}

function scenarioHeading(group: SwissCutGroup): string {
  return `晋级边缘：${group.boundaryRecord}`
}

calculate()
</script>

<template>
  <div class="page-shell swiss-calculator-page">
    <header class="page-heading">
      <RouterLink class="back-link" to="/tools">← 返回实用工具</RouterLink>
      <h1>瑞士轮计算器</h1>
      <p>根据玩家人数、回合数和晋级人数，计算出轮附近可能出现的战绩人数与晋级名额。</p>
    </header>

    <div class="swiss-calculator-layout">
      <section class="calculator-panel" aria-labelledby="calculator-settings-title">
        <div class="calculator-panel-heading">
          <h2 id="calculator-settings-title">比赛设置</h2>
          <p>奇数人数产生的轮空将自动计入计算。</p>
        </div>
        <form class="content-form calculator-form" @submit.prevent="calculate">
          <label>
            <span>玩家人数</span>
            <input v-model.number="form.playerCount" type="number" min="2" max="1024" required />
          </label>
          <label>
            <span>瑞士轮回合数</span>
            <input v-model.number="form.roundCount" type="number" min="1" max="12" required />
          </label>
          <label>
            <span>晋级人数（Top N）</span>
            <input v-model.number="form.topCut" type="number" min="1" :max="form.playerCount" required />
          </label>
          <div class="form-actions">
            <button class="button primary" type="submit">计算出轮情况</button>
          </div>
        </form>
      </section>

      <section class="calculator-panel calculator-result-panel" aria-labelledby="calculator-result-title">
        <div class="calculator-panel-heading">
          <h2 id="calculator-result-title">计算结果</h2>
          <p>只展示会影响晋级线的战绩情况。</p>
        </div>
        <FormMessage v-if="error" :message="error" />
        <template v-else-if="result">
          <div class="calculator-result-summary">
            <span>保底晋级战绩</span>
            <strong>{{ result.guaranteedRecord }}</strong>
            <p v-if="maximumRisk?.misses">
              最多可能有 {{ maximumRisk.misses }} 名 {{ maximumRisk.record }} 玩家无法晋级。
            </p>
            <p v-else>晋级边缘战绩在所有计算情况中均可晋级。</p>
          </div>

          <section v-for="group in result.groups" :key="group.boundaryWins" class="calculator-case-group">
            <h3>{{ scenarioHeading(group) }}</h3>
            <div class="calculator-result-table-wrap">
              <table class="calculator-result-table">
                <thead>
                  <tr>
                    <th>情况</th>
                    <th>{{ group.higherRecordLabel }}</th>
                    <th>{{ group.boundaryRecord }} 人数</th>
                    <th>{{ group.boundaryRecord }} 晋级</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(scenario, index) in group.scenarios" :key="`${group.boundaryWins}-${index}`">
                    <td>{{ index + 1 }}</td>
                    <td>{{ scenario.higherRecordCount }}</td>
                    <td>{{ scenario.boundaryPlayerCount }}</td>
                    <td>{{ scenario.boundaryQualifiers }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <p class="calculator-note">
            同战绩玩家的具体名次仍由 OMW、败局轮次小分和直接交手决定。
          </p>
        </template>
      </section>
    </div>
  </div>
</template>
