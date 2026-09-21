import { describe, expect, it, vi } from 'vitest'

import { createLiveRefreshController } from '../src/composables/useLiveRefresh'

function createEnvironment() {
  let visible = true
  let focusListener: (() => void) | null = null
  let visibilityListener: (() => void) | null = null
  let intervalCallback: (() => void) | null = null
  const clearInterval = vi.fn()
  const setInterval = vi.fn((callback: () => void) => {
    intervalCallback = callback
    return 42
  })
  return {
    environment: {
      isVisible: () => visible,
      setInterval,
      clearInterval,
      addFocusListener: (listener: () => void) => { focusListener = listener },
      removeFocusListener: vi.fn(),
      addVisibilityListener: (listener: () => void) => { visibilityListener = listener },
      removeVisibilityListener: vi.fn(),
    },
    setVisible: (value: boolean) => { visible = value },
    triggerFocus: () => focusListener?.(),
    triggerVisibility: () => visibilityListener?.(),
    triggerInterval: () => intervalCallback?.(),
    setInterval,
    clearInterval,
  }
}

describe('live refresh controller', () => {
  it('polls only when enabled and refreshes when the page regains focus', async () => {
    const refresh = vi.fn().mockResolvedValue(undefined)
    let live = true
    const testEnvironment = createEnvironment()
    const controller = createLiveRefreshController(refresh, {
      intervalMs: 10_000,
      pollWhen: () => live,
    }, testEnvironment.environment)

    controller.start()
    expect(testEnvironment.setInterval).toHaveBeenCalledWith(expect.any(Function), 10_000)

    testEnvironment.triggerInterval()
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledTimes(1))

    testEnvironment.triggerFocus()
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledTimes(2))

    live = false
    controller.syncPolling()
    expect(testEnvironment.clearInterval).toHaveBeenCalledWith(42)
  })

  it('pauses refreshes while the page is hidden and refreshes when visible again', async () => {
    const refresh = vi.fn().mockResolvedValue(undefined)
    const testEnvironment = createEnvironment()
    const controller = createLiveRefreshController(refresh, {}, testEnvironment.environment)
    controller.start()

    testEnvironment.setVisible(false)
    testEnvironment.triggerFocus()
    await Promise.resolve()
    expect(refresh).not.toHaveBeenCalled()

    testEnvironment.setVisible(true)
    testEnvironment.triggerVisibility()
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce())
  })
})
