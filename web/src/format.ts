import { t } from './texts'

const NBSP = '\u00a0'

/** "1868413480" -> "1 868 413 480" without converting to a float. */
export function formatAmount(value: string): string {
  const negative = value.startsWith('-')
  const digits = negative ? value.slice(1) : value
  const [whole, fraction] = digits.split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP)
  return `${negative ? '−' : ''}${grouped}${fraction ? `,${fraction}` : ''}`
}

export function formatUzs(value: string): string {
  return `${formatAmount(value)}${NBSP}${t.currency}`
}

/** "2026-10-12" -> "12.10.2026". */
export function formatDate(value: string | null): string {
  if (!value) return '—'
  const [year, month, day] = value.split('-')
  return `${day}.${month}.${year}`
}

/** Today's date in the device time zone as YYYY-MM-DD. */
export function todayIso(): string {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

/** Keeps only digits, without leading zeros: "1 500 000 сум" -> "1500000". */
export function digitsOnly(value: string): string {
  return value.replace(/\D/g, '').replace(/^0+(?=\d)/, '')
}

/** Indicative balance after a payment; exact integer math (BigInt), for display only. */
export function balanceAfterPayment(balance: string, amount: string): string {
  return (BigInt(balance) - BigInt(amount)).toString()
}

export type BalanceKind = 'debt' | 'credit' | 'zero'

export function balanceKind(balance: string): BalanceKind {
  if (balance.startsWith('-')) return 'credit'
  return /^0+$/.test(balance) ? 'zero' : 'debt'
}

/** Text label plus absolute amount, so debt and credit never depend on colour alone. */
export function describeBalance(balance: string): { kind: BalanceKind; label: string; amount: string } {
  const kind = balanceKind(balance)
  const absolute = kind === 'credit' ? balance.slice(1) : balance
  const label = kind === 'debt' ? t.debt : kind === 'credit' ? t.credit : t.settled
  return { kind, label, amount: kind === 'zero' ? '' : formatUzs(absolute) }
}
