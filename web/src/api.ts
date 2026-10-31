import { initData } from './telegram'
import { t } from './texts'

// Mirrors sheepbot/api/schemas.py. Money values are strings.
export type Permission = 'upload' | 'view' | 'admin'

export type Me = {
  id: number
  telegram_id: number
  full_name: string
  username: string | null
  status: string
  status_label: string
  permissions: Permission[]
}

export type BalanceFilter = 'all' | 'debt' | 'credit' | 'zero'

export type ClientBalance = {
  id: number
  name: string
  shipped: string
  paid: string
  balance: string
  last_sale_date: string | null
  last_payment_date: string | null
}

export type ClientPage = { items: ClientBalance[]; total: number }

export type ClientDetail = ClientBalance & { phone: string | null }

export type Option = { value: string; label: string }

export type Catalog = { payment_methods: Option[] }

export type LedgerLine = {
  date: string
  kind: 'shipment' | 'payment'
  trip_number: number | null
  product: string | null
  heads: number | null
  net_kg: string | null
  price_uzs_per_kg: string | null
  amount_uzs: string
  payment_method: string | null
  note: string | null
  running_balance: string
}

export type Ledger = {
  client_id: number
  client_name: string
  opening_balance: string
  shipped: string
  paid: string
  closing_balance: string
  lines: LedgerLine[]
}

export type Payment = {
  id: number
  client_id: number
  client_name: string
  amount_uzs: string
  method: string
  method_label: string
  date: string
  note: string | null
  entered_by: string
  created_at: string
}

export type PaymentPage = { items: Payment[]; total: number }

export type PaymentResult = { payment: Payment; balance: string }

export type ClientInput = { name: string; phone: string | null }

export type PaymentInput = {
  client_id: number
  amount_uzs: string
  method: string
  date: string
  note: string | null
}

export class ApiError extends Error {
  readonly status: number
  readonly fields: Record<string, string>

  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }

  get isAuth(): boolean {
    return this.status === 401 || this.status === 403
  }
}

/** Message and per-field errors from a failed request. */
export function errorDetails(error: unknown): { message: string; fields: Record<string, string> } {
  if (error instanceof ApiError) return { message: error.message, fields: error.fields }
  return { message: t.serverError, fields: {} }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (initData) headers.set('Authorization', `tma ${initData}`)
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, t.networkError)
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const message = typeof body?.detail === 'string' ? body.detail : t.serverError
    throw new ApiError(response.status, message, body?.fields ?? {})
  }
  return body as T
}

function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export const api = {
  me: () => request<Me>('/me'),
  catalog: () => request<Catalog>('/catalog'),
  clients: (params: { q: string; filter: BalanceFilter; offset: number; limit: number }) => {
    const query = new URLSearchParams({
      q: params.q,
      filter: params.filter,
      offset: String(params.offset),
      limit: String(params.limit),
    })
    return request<ClientPage>(`/clients?${query}`)
  },
  client: (id: number) => request<ClientDetail>(`/clients/${id}`),
  createClient: (input: ClientInput) => send<ClientDetail>('POST', '/clients', input),
  updateClient: (id: number, input: ClientInput) =>
    send<ClientDetail>('PATCH', `/clients/${id}`, input),
  ledger: (id: number) => request<Ledger>(`/clients/${id}/ledger`),
  payments: (params: { offset: number; limit: number }) =>
    request<PaymentPage>(`/payments?offset=${params.offset}&limit=${params.limit}`),
  createPayment: (input: PaymentInput) => send<PaymentResult>('POST', '/payments', input),
  deletePayment: (id: number) => send<PaymentResult>('DELETE', `/payments/${id}`),
}
