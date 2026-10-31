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

export type TripListItem = {
  number: number
  departure_date: string
  purchased_heads: number
  revenue: string
  cost: string
  profit: string
  margin_pct: string | null
}

export type TripPage = { items: TripListItem[]; total: number }

export type TripPurchaseRow = {
  type_label: string
  heads: number
  net_kg: string
  amount_kzt: string
  amount_uzs: string
}

export type TripSummary = {
  number: number
  departure_date: string
  arrival_date: string | null
  rate_kzt: string
  rate_usd: string
  note: string | null
  purchases: TripPurchaseRow[]
  purchase_total: TripPurchaseRow
  expenses_uzs: string
  sales_by_product: {
    product_name: string
    heads: number
    net_kg: string
    avg_price_uzs: string
    amount_uzs: string
  }[]
  sales_by_client: { client_name: string; heads: number; net_kg: string; amount_uzs: string }[]
  economics: {
    type_label: string
    purchased_heads: number
    sold_heads: number
    cost_per_kg: string | null
    avg_sale_price: string | null
    diff_per_kg: string | null
  }[]
  revenue: string
  cost: string
  profit: string
  margin_pct: string | null
}

export type Debtors = {
  rows: {
    client_id: number
    name: string
    balance: string
    last_sale_date: string | null
    last_payment_date: string | null
  }[]
  total_debt: string
  total_credit: string
  net: string
}

export type User = {
  id: number
  telegram_id: number
  full_name: string
  username: string | null
  status: 'pending' | 'active' | 'blocked'
  status_label: string
  can_upload: boolean
  can_view: boolean
}

export type UserUpdate = Partial<Pick<User, 'can_upload' | 'can_view' | 'status'>>

export type ReportKind = 'statement' | 'trip' | 'debtors'
export type ReportFormat = 'pdf' | 'xlsx'

/** Query for one report: kind-specific parameters plus the file format. */
export type ReportRequest = {
  kind: ReportKind
  format: ReportFormat
  client_id?: number
  number?: number
  date_from?: string
  date_to?: string
}

function reportPath(report: ReportRequest, send: boolean): string {
  const params = new URLSearchParams({ format: report.format })
  for (const key of ['client_id', 'number', 'date_from', 'date_to'] as const) {
    const value = report[key]
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  return `/reports/${report.kind}${send ? '/send' : ''}?${params}`
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

async function fetchApi(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (initData) headers.set('Authorization', `tma ${initData}`)
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, t.networkError)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const message = typeof body?.detail === 'string' ? body.detail : t.serverError
    throw new ApiError(response.status, message, body?.fields ?? {})
  }
  return response
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetchApi(path, init)
  return (await response.json()) as T
}

/** Downloads an authenticated file response (the Authorization header can't go in a link). */
async function download(path: string): Promise<void> {
  const response = await fetchApi(path)
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const encoded = /filename\*=UTF-8''([^;]+)/.exec(disposition)?.[1]
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = encoded ? decodeURIComponent(encoded) : 'report'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
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
  trips: (params: { offset: number; limit: number }) =>
    request<TripPage>(`/trips?offset=${params.offset}&limit=${params.limit}`),
  trip: (number: number) => request<TripSummary>(`/trips/${number}`),
  debtors: () => request<Debtors>('/debtors'),
  downloadReport: (report: ReportRequest) => download(reportPath(report, false)),
  sendReport: (report: ReportRequest) =>
    send<{ filename: string }>('POST', reportPath(report, true)),
  users: () => request<User[]>('/users'),
  updateUser: (id: number, update: UserUpdate) => send<User>('PATCH', `/users/${id}`, update),
}
