<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

withDefaults(defineProps<{ showCompetitionTabs?: boolean }>(), {
  showCompetitionTabs: false,
})

const route = useRoute()
const competitionModuleSelected = computed(() => ['/tournaments', '/my-tournaments'].includes(route.path))
const reportModuleSelected = computed(() => route.path.startsWith('/reports'))
const competitionTab = computed(() => {
  if (route.path === '/tournaments') return 'matches'
  return route.query.tab === 'created' ? 'created' : 'joined'
})
</script>

<template>
  <nav class="tournament-module-nav" aria-label="赛事中心模块">
    <RouterLink :class="{ 'module-selected': competitionModuleSelected }" to="/tournaments">比赛中心</RouterLink>
    <RouterLink :class="{ 'module-selected': reportModuleSelected }" to="/reports">赛事周报</RouterLink>
  </nav>
  <nav v-if="showCompetitionTabs" class="competition-tabs" aria-label="比赛中心内容">
    <RouterLink :class="{ 'tab-selected': competitionTab === 'matches' }" to="/tournaments">比赛</RouterLink>
    <RouterLink :class="{ 'tab-selected': competitionTab === 'joined' }" to="/my-tournaments">我参加的</RouterLink>
    <RouterLink :class="{ 'tab-selected': competitionTab === 'created' }" :to="{ path: '/my-tournaments', query: { tab: 'created' } }">我发布的</RouterLink>
  </nav>
</template>
