import { keepPreviousData, useInfiniteQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api, type BalanceFilter } from '../api'
import { Balance, ErrorState, Loading } from '../components'
import { formatDate } from '../format'
import { useCanUpload } from '../hooks'
import { t } from '../texts'

const PAGE_SIZE = 50
const SEARCH_DELAY_MS = 300

const FILTERS: { value: BalanceFilter; label: string }[] = [
  { value: 'all', label: t.filterAll },
  { value: 'debt', label: t.filterDebt },
  { value: 'credit', label: t.filterCredit },
  { value: 'zero', label: t.filterZero },
]

function parseFilter(value: string | null): BalanceFilter {
  return FILTERS.some((f) => f.value === value) ? (value as BalanceFilter) : 'all'
}

export function ClientsPage() {
  // Search and filter live in the URL so they survive navigating to a client and back.
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const filter = parseFilter(params.get('filter'))
  const [input, setInput] = useState(q)

  useEffect(() => {
    if (input.trim() === q) return
    const timer = setTimeout(() => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (input.trim()) next.set('q', input.trim())
          else next.delete('q')
          return next
        },
        { replace: true },
      )
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [input, q, setParams])

  const setFilter = (value: BalanceFilter) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (value === 'all') next.delete('filter')
        else next.set('filter', value)
        return next
      },
      { replace: true },
    )

  const clients = useInfiniteQuery({
    queryKey: ['clients', q, filter],
    queryFn: ({ pageParam }) => api.clients({ q, filter, offset: pageParam, limit: PAGE_SIZE }),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0)
      return loaded < last.total ? loaded : undefined
    },
    placeholderData: keepPreviousData,
  })

  const items = clients.data?.pages.flatMap((page) => page.items) ?? []
  const total = clients.data?.pages[0]?.total ?? 0
  const searching = q !== '' || filter !== 'all'
  const canUpload = useCanUpload()

  return (
    <>
      <header className="page-header">
        <div className="header-row">
          <h1>{t.clientsTitle}</h1>
          {canUpload && (
            <Link className="button small-button" to="/clients/new">
              {t.addClient}
            </Link>
          )}
        </div>
        <input
          type="search"
          className="search"
          placeholder={t.searchPlaceholder}
          aria-label={t.searchPlaceholder}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          maxLength={100}
        />
        <div className="chips" role="group">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              className="chip"
              aria-pressed={filter === f.value}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </header>

      {clients.isPending ? (
        <Loading />
      ) : clients.isError ? (
        <ErrorState error={clients.error} onRetry={() => clients.refetch()} />
      ) : items.length === 0 ? (
        <p className="state">{searching ? t.noMatches : t.noClients}</p>
      ) : (
        <>
          <p className="muted count">{t.found(total)}</p>
          <ul className="list">
            {items.map((client) => (
              <li key={client.id}>
                <Link to={`/clients/${client.id}`} className="row">
                  <span className="row-main">
                    <span className="row-title">{client.name}</span>
                    <span className="muted small">
                      {t.lastSale}: {formatDate(client.last_sale_date)} · {t.lastPayment}:{' '}
                      {formatDate(client.last_payment_date)}
                    </span>
                  </span>
                  <Balance value={client.balance} />
                </Link>
              </li>
            ))}
          </ul>
          {clients.hasNextPage && (
            <button
              type="button"
              className="button wide"
              disabled={clients.isFetchingNextPage}
              onClick={() => clients.fetchNextPage()}
            >
              {clients.isFetchingNextPage ? t.loading : t.showMore}
            </button>
          )}
        </>
      )}
    </>
  )
}
