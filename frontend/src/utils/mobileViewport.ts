const VIEWPORT_SETTLE_DELAY_MS = 100
const VIEWPORT_SETTLE_TIMEOUT_MS = 450

function waitForNextPaint(): Promise<void> {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => resolve()))
  })
}

/**
 * Releases form focus before a route change so mobile browsers can restore the
 * visual viewport after closing the on-screen keyboard.
 */
export async function prepareViewportForNavigation(): Promise<void> {
  const activeElement = document.activeElement
  if (!(activeElement instanceof HTMLElement)) return

  const viewport = window.visualViewport

  if (!viewport) {
    activeElement.blur()
    await waitForNextPaint()
    return
  }

  await new Promise<void>((resolve) => {
    let settleTimer: number | undefined
    let timeoutTimer: number | undefined

    const finish = () => {
      if (settleTimer !== undefined) window.clearTimeout(settleTimer)
      if (timeoutTimer !== undefined) window.clearTimeout(timeoutTimer)
      viewport.removeEventListener('resize', scheduleFinish)
      viewport.removeEventListener('scroll', scheduleFinish)
      resolve()
    }

    const scheduleFinish = () => {
      if (settleTimer !== undefined) window.clearTimeout(settleTimer)
      settleTimer = window.setTimeout(finish, VIEWPORT_SETTLE_DELAY_MS)
    }

    viewport.addEventListener('resize', scheduleFinish)
    viewport.addEventListener('scroll', scheduleFinish)
    timeoutTimer = window.setTimeout(finish, VIEWPORT_SETTLE_TIMEOUT_MS)
    activeElement.blur()
    window.requestAnimationFrame(scheduleFinish)
  })

  await waitForNextPaint()
}
