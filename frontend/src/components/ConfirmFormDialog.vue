<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'

defineProps<{
  title: string
  description: string
  confirmText: string
  busy?: boolean
  error?: string
  reason?: string
  reasonLabel?: string
  reasonPlaceholder?: string
  reasonMaxlength?: number
}>()

const emit = defineEmits<{
  cancel: []
  confirm: []
  'update:reason': [value: string]
}>()

const cancelButton = ref<HTMLButtonElement | null>(null)

onMounted(async () => {
  await nextTick()
  cancelButton.value?.focus()
})

function cancel() {
  emit('cancel')
}

function updateReason(event: Event) {
  if (event.target instanceof HTMLTextAreaElement) emit('update:reason', event.target.value)
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
        <label v-if="reasonLabel" class="form-dialog-field">
          <span>{{ reasonLabel }}</span>
          <textarea
            :value="reason"
            :maxlength="reasonMaxlength ?? 500"
            :placeholder="reasonPlaceholder"
            rows="3"
            :disabled="busy"
            @input="updateReason"
          />
        </label>
        <p v-if="error" class="form-dialog-error" role="alert">{{ error }}</p>
        <div class="form-actions">
          <button ref="cancelButton" class="button secondary" type="button" :disabled="busy" @click="cancel">取消</button>
          <button class="button primary" type="submit" :disabled="busy">{{ busy ? '提交中…' : confirmText }}</button>
        </div>
      </form>
    </div>
  </Teleport>
</template>
