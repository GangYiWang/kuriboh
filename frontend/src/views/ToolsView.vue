<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="page-shell tools-page">
    <header class="page-heading">
      <h1>实用工具</h1>
    </header>

    <section class="tool-list" aria-labelledby="tool-list-title">
      <h2 id="tool-list-title" class="visually-hidden">工具列表</h2>
      <RouterLink to="/tools/swiss-calculator">
        <span>01</span>
        <div>
          <h2>瑞士轮计算器</h2>
          <p>计算出轮附近的可能战绩人数与晋级名额。</p>
        </div>
        <i>→</i>
      </RouterLink>
    </section>
  </div>
</template>
