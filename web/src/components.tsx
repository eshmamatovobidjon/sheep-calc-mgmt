import { type ReactNode, useCallback, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router'
import { ApiError, type Permission } from './api'
import { describeBalance } from './format'
import { bindBackButton, nativeBackButton } from './telegram'
import { t } from './texts'

export function Loading() {
  return <p className="state">{t.loading}</p>
}

/** One-off message passed through navigation state, e.g. "Клиент сохранён." */
export function Notice() {
  const notice = (useLocation().state as { notice?: string } | null)?.notice
  return notice ? (
    <p className="notice" role="status">
      {notice}
    </p>
  ) : null
}

export function Field({
  label,
  error,
  hint,
  group = false,
  children,
}: {
  label: string
  error?: string
  hint?: string
  /** True for a set of buttons; a <label> may only wrap a single form control. */
  group?: boolean
  children: ReactNode
}) {
  const content = (
    <>
      <span className="field-label">{label}</span>
      {children}
      {error ? (
        <span className="field-error">{error}</span>
      ) : (
        hint && <span className="muted small">{hint}</span>
      )}
    </>
  )
  return group ? (
    <div className="field" role="group" aria-label={label}>
      {content}
    </div>
  ) : (
    <label className="field">{content}</label>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof ApiError ? error.message : t.serverError
  // Retrying cannot fix a 4xx (not found, no access, invalid input).
  const retryable = !(error instanceof ApiError && error.status >= 400 && error.status < 500)
  return (
    <div className="state" role="alert">
      <p>{message}</p>
      {onRetry && retryable && (
        <button type="button" className="button" onClick={onRetry}>
          {t.retry}
        </button>
      )}
    </div>
  )
}

export function Balance({ value }: { value: string }) {
  const { kind, label, amount } = describeBalance(value)
  return (
    <span className={`balance balance-${kind}`}>
      <span className="balance-label">{label}</span>
      {amount && <span className="balance-amount">{amount}</span>}
    </span>
  )
}

/** Telegram back button on sub-pages; an in-app link where the native one is unavailable. */
export function BackLink({ fallback = '/clients' }: { fallback?: string }) {
  const navigate = useNavigate()
  const location = useLocation()
  const goBack = useCallback(() => {
    if (location.key === 'default') navigate(fallback, { replace: true })
    else navigate(-1)
  }, [fallback, location.key, navigate])

  useEffect(() => bindBackButton(true, goBack), [goBack])

  if (nativeBackButton) return null
  return (
    <button type="button" className="back" onClick={goBack}>
      ← {t.back}
    </button>
  )
}

const NAV_ITEMS: { to: string; label: string; permissions: Permission[] }[] = [
  { to: '/clients', label: t.navClients, permissions: ['upload', 'view'] },
  { to: '/payments', label: t.navPayments, permissions: ['upload'] },
]

export function BottomNav({ permissions }: { permissions: Permission[] }) {
  const items = NAV_ITEMS.filter(
    (item) => permissions.includes('admin') || item.permissions.some((p) => permissions.includes(p)),
  )
  return (
    <nav className="bottom-nav">
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} className="bottom-nav-item">
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}
