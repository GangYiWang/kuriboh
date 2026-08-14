<script setup lang="ts">
defineProps<{ type?: 'error' | 'success'; message: string }>()
</script>

<template>
  <p :class="['form-message', type ?? 'error']" role="status">{{ message }}</p>
</template>
