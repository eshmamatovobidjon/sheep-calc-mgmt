import { useInfiniteQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { api } from '../api'
import { ErrorState, Loading } from '../components'
import { formatDate, formatPercent, formatUzs } from '../format'
import { t } from '../texts'

const PAGE_SIZE = 20

export function TripsPage() {
  const trips = useInfiniteQuery({
    queryKey: ['trips'],
    queryFn: ({ pageParam }) => api.trips({ offset: pageParam, limit: PAGE_SIZE }),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0)
      return loaded < last.total ? loaded : undefined
    },
  })
  const items = trips.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <>
      <header className="page-header">
        <h1>{t.tripsTitle}</h1>
      </header>
      {trips.isPending ? (
        <Loading />
      ) : trips.isError ? (
        <ErrorState error={trips.error} onRetry={() => trips.refetch()} />
      ) : items.length === 0 ? (
        <p className="state">{t.noTrips}</p>
      ) : (
        <>
          <ul className="list">
            {items.map((trip) => (
              <li key={trip.number}>
                <Link to={`/trips/${trip.number}`} className="row">
                  <span className="row-main">
                    <span className="row-title">{t.tripNumber(trip.number)}</span>
                    <span className="muted small">
                      {formatDate(trip.departure_date)} · {t.heads(trip.purchased_heads)} ·{' '}
                      {t.revenue}: {formatUzs(trip.revenue)}
                    </span>
                  </span>
                  <span className="balance">
                    <span className="balance-label">{t.profit}</span>
                    <span
                      className={`balance-amount ${trip.profit.startsWith('-') ? 'balance-debt' : 'balance-credit'}`}
                    >
                      {formatUzs(trip.profit)}
                    </span>
                    <span className="muted small">{formatPercent(trip.margin_pct)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {trips.hasNextPage && (
            <button
              type="button"
              className="button wide"
              disabled={trips.isFetchingNextPage}
              onClick={() => trips.fetchNextPage()}
            >
              {trips.isFetchingNextPage ? t.loading : t.showMore}
            </button>
          )}
        </>
      )}
    </>
  )
}
