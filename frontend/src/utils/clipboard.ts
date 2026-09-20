function copyWithSelection(value: string): void {
  const textarea = document.createElement('textarea')
  textarea.value = value
  textarea.readOnly = true
  textarea.style.position = 'fixed'
  textarea.style.inset = '0 auto auto 0'
  textarea.style.width = '1px'
  textarea.style.height = '1px'
  textarea.style.opacity = '0'
  textarea.style.pointerEvents = 'none'
  document.body.appendChild(textarea)

  try {
    textarea.focus()
    textarea.select()
    textarea.setSelectionRange(0, value.length)
    if (!document.execCommand('copy')) {
      throw new Error('COPY_COMMAND_REJECTED')
    }
  } finally {
    textarea.remove()
  }
}

export async function copyText(value: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value)
      return
    } catch {
      // Fall back for denied clipboard permissions and non-secure deployments.
    }
  }

  copyWithSelection(value)
}
