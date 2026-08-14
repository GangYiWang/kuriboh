<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'

defineProps<{
  title: string
  description: string
  confirmText: string
  busy?: boolean
  error?: string
}>()

const emit = defineEmits<{
  cancel: []
  confirm: []
}>()

const cancelButton = ref<HTMLButtonElement | null>(null)

onMounted(async () => {
  await nextTick()
  cancelButton.value?.focus()
})

function cancel() {
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div class="form-dialog-backdrop" @mousedown.self="cancel">
      <form
        class="form-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        @submit.prevent="emit('confirm')"
        @keydown.esc.prevent="cancel"
      >
        <header>
          <p class="section-kicker">CONFIRM ACTION</p>
          <h2>{{ title }}</h2>
        </header>
        <p class="form-dialog-description">{{ description }}</p>
        <p v-if="error" class="form-dialog-error" role="alert">{{ error }}</p>
        <div class="form-actions">
          <button ref="cancelButton" class="button secondary" type="button" :disabled="busy" @click="cancel">取消</button>
          <button class="button primary" type="submit" :disabled="busy">{{ busy ? '提交中…' : confirmText }}</button>
        </div>
      </form>
    </div>
  </Teleport>
</template>
