// Thin wrapper over the official telegram-web-app.js (loaded in index.html).

type BackButton = {
  show(): void
  hide(): void
  onClick(callback: () => void): void
  offClick(callback: () => void): void
}

type WebApp = {
  initData: string
  platform: string
  ready(): void
  expand(): void
  isVersionAtLeast(version: string): boolean
  BackButton: BackButton
}

declare global {
  interface Window {
    Telegram?: { WebApp?: WebApp }
  }
}

const webApp = window.Telegram?.WebApp

/** Raw signed launch data; empty outside Telegram. */
export const initData = webApp?.initData ?? ''

export const insideTelegram = Boolean(webApp && webApp.platform !== 'unknown')

export const nativeBackButton = Boolean(insideTelegram && webApp?.isVersionAtLeast('6.1'))

export function initTelegram(): void {
  webApp?.ready()
  webApp?.expand()
}

/** Shows Telegram's native back button while `visible` (no-op outside Telegram); returns cleanup. */
export function bindBackButton(visible: boolean, onBack: () => void): () => void {
  if (!nativeBackButton || !webApp) return () => {}
  const button = webApp.BackButton
  if (!visible) {
    button.hide()
    return () => {}
  }
  button.onClick(onBack)
  button.show()
  return () => {
    button.offClick(onBack)
    button.hide()
  }
}
