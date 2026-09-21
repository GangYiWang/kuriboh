import { onBeforeUnmount, onMounted, watch } from 'vue'

export interface LiveRefreshOptions {
  intervalMs?: number
  pollWhen?: () => boolean
  onError?: (error: unknown) => void
}

interface LiveRefreshEnvironment {
  isVisible: () => boolean
  setInterval: (callback: () => void, intervalMs: number) => number
  clearInterval: (intervalId: number) => void
  addFocusListener: (listener: () => void) => void
  removeFocusListener: (listener: () => void) => void
  addVisibilityListener: (listener: () => void) => void
  removeVisibilityListener: (listener: () => void) => void
}

export interface LiveRefreshController {
  refreshNow: () => Promise<void>
  start: () => void
  stop: () => void
  syncPolling: () => void
}

function browserEnvironment(): LiveRefreshEnvironment {
  return {
    isVisible: () => document.visibilityState !== 'hidden',
    setInterval: (callback, intervalMs) => window.setInterval(callback, intervalMs),
    clearInterval: (intervalId) => window.clearInterval(intervalId),
    addFocusListener: (listener) => window.addEventListener('focus', listener),
    removeFocusListener: (listener) => window.removeEventListener('focus', listener),
    addVisibilityListener: (listener) => document.addEventListener('visibilitychange', listener),
    removeVisibilityListener: (listener) => document.removeEventListener('visibilitychange', listener),
  }
}

export function createLiveRefreshController(
  refresh: () => Promise<void>,
  options: LiveRefreshOptions = {},
  environment: LiveRefreshEnvironment = browserEnvironment(),
): LiveRefreshController {
  const intervalMs = options.intervalMs ?? 10_000
  let intervalId: number | null = null
  let started = false
  let running = false

  async function refreshNow(): Promise<void> {
    if (!started || running || !environment.isVisible()) return
    running = true
    try {
      await refresh()
    } catch (error) {
      options.onError?.(error)
    } finally {
      running = false
    }
  }

  function clearPolling(): void {
    if (intervalId === null) return
    environment.clearInterval(intervalId)
    intervalId = null
  }

  function syncPolling(): void {
    clearPolling()
    if (!started || !options.pollWhen?.()) return
    intervalId = environment.setInterval(() => {
      void refreshNow()
    }, intervalMs)
  }

  function handleFocus(): void {
    void refreshNow()
  }

  function handleVisibilityChange(): void {
    if (environment.isVisible()) void refreshNow()
  }

  function start(): void {
    if (started) return
    started = true
    environment.addFocusListener(handleFocus)
    environment.addVisibilityListener(handleVisibilityChange)
    syncPolling()
  }

  function stop(): void {
    if (!started) return
    started = false
    clearPolling()
    environment.removeFocusListener(handleFocus)
    environment.removeVisibilityListener(handleVisibilityChange)
  }

  return { refreshNow, start, stop, syncPolling }
}

export function useLiveRefresh(
  refresh: () => Promise<void>,
  options: LiveRefreshOptions = {},
): Pick<LiveRefreshController, 'refreshNow'> {
  const controller = createLiveRefreshController(refresh, options)
  if (options.pollWhen) watch(options.pollWhen, controller.syncPolling)
  onMounted(controller.start)
  onBeforeUnmount(controller.stop)
  return { refreshNow: controller.refreshNow }
}
