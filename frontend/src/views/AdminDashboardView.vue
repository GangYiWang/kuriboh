<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { MESSAGING_ENABLED } from '@/config/features'
</script>

<template>
  <div class="page-shell admin-page">
    <header class="page-heading"><p class="section-kicker">ADMINISTRATION</p><h1>管理后台</h1><p>平台内容发布与全局操作审计。</p></header>
    <div class="admin-modules">
      <RouterLink to="/admin/banlists"><span>01</span><div><h2>禁卡表版本</h2><p>发布自动递增的新版本，查看永久历史。</p></div><i>→</i></RouterLink>
      <RouterLink to="/admin/announcements"><span>02</span><div><h2>平台公告</h2><p>发布和更新公告，管理置顶状态。</p></div><i>→</i></RouterLink>
      <RouterLink v-if="MESSAGING_ENABLED" to="/admin/messages"><span>03</span><div><h2>平台通知</h2><p>向全部注册账号发送重要站内通知。</p></div><i>→</i></RouterLink>
      <RouterLink to="/admin/audit"><span>{{ MESSAGING_ENABLED ? '04' : '03' }}</span><div><h2>操作审计</h2><p>复查平台级操作和不可逆发布记录。</p></div><i>→</i></RouterLink>
    </div>
  </div>
</template>
