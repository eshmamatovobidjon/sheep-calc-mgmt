import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { api } from '../api'
import { BackLink, ErrorState, Loading } from '../components'
import { formatAmount, formatDate, formatPercent, formatRate, formatUzs } from '../format'
import { useMe } from '../hooks'
import { t } from '../texts'

function Kg({ value }: { value: string }) {
  return (
    <>
      {formatAmount(value)} {t.kg}
    </>
  )
}

export function TripPage() {
  const number = Number(useParams().number)
  const valid = Number.isInteger(number) && number > 0
  const canView = useMe().data?.permissions.includes('view') ?? false
  const trip = useQuery({
    queryKey: ['trip', number],
    queryFn: () => api.trip(number),
    enabled: valid,
  })

  if (!valid) {
    return (
      <>
        <BackLink fallback="/trips" />
        <p className="state">{t.tripNotFound}</p>
      </>
    )
  }
  if (trip.isPending) {
    return (
      <>
        <BackLink fallback="/trips" />
        <Loading />
      </>
    )
  }
  if (trip.isError) {
    return (
      <>
        <BackLink fallback="/trips" />
        <ErrorState error={trip.error} onRetry={() => trip.refetch()} />
      </>
    )
  }

  const d = trip.data
  return (
    <>
      <BackLink fallback="/trips" />
      <article className="card">
        <h1>{t.tripNumber(d.number)}</h1>
        <p className="muted small">
          {t.departure}: {formatDate(d.departure_date)}
          {d.arrival_date && ` · ${t.arrival}: ${formatDate(d.arrival_date)}`} · {t.rates}: KZT{' '}
          {formatRate(d.rate_kzt)}, USD {formatRate(d.rate_usd)}
        </p>
        {d.note && <p className="muted small">{d.note}</p>}
        <dl className="facts">
          <dt>{t.revenue}</dt>
          <dd className="num">{formatUzs(d.revenue)}</dd>
          <dt>{t.cost}</dt>
          <dd className="num">{formatUzs(d.cost)}</dd>
          <dt>{t.profit}</dt>
          <dd className={`num ${d.profit.startsWith('-') ? 'balance-debt' : 'balance-credit'}`}>
            {formatUzs(d.profit)}
          </dd>
          <dt>{t.marginOnCost}</dt>
          <dd className="num">{formatPercent(d.margin_pct)}</dd>
        </dl>
        {canView && (
          <div className="actions">
            <Link className="button secondary" to={`/reports?kind=trip&number=${d.number}`}>
              {t.tripReport}
            </Link>
          </div>
        )}
      </article>

      <section className="card">
        <h2>{t.purchases}</h2>
        <ul className="ledger">
          {[...d.purchases, d.purchase_total].map((row, index) => (
            <li key={index} className="ledger-row">
              <div className="row-main">
                <span className="row-title">
                  {index === d.purchases.length ? t.total : row.type_label}
                </span>
                <span className="muted small">
                  {t.heads(row.heads)} · <Kg value={row.net_kg} /> · {formatAmount(row.amount_kzt)} KZT
                </span>
              </div>
              <span className="num">{formatUzs(row.amount_uzs)}</span>
            </li>
          ))}
          <li className="ledger-row">
            <span className="row-title">{t.expenses}</span>
            <span className="num">{formatUzs(d.expenses_uzs)}</span>
          </li>
        </ul>
      </section>

      <section className="card">
        <h2>{t.economics}</h2>
        <ul className="ledger">
          {d.economics.map((row) => (
            <li key={row.type_label} className="ledger-row">
              <div className="row-main">
                <span className="row-title">{row.type_label}</span>
                <span className="muted small">{t.soldOf(row.sold_heads, row.purchased_heads)}</span>
              </div>
              <dl className="facts compact">
                <dt>{t.costPerKg}</dt>
                <dd className="num">{row.cost_per_kg ? formatAmount(row.cost_per_kg) : '—'}</dd>
                <dt>{t.salePerKg}</dt>
                <dd className="num">{row.avg_sale_price ? formatAmount(row.avg_sale_price) : '—'}</dd>
                <dt>{t.diffPerKg}</dt>
                <dd className="num">{row.diff_per_kg ? formatAmount(row.diff_per_kg) : '—'}</dd>
              </dl>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>{t.salesByProduct}</h2>
        <ul className="ledger">
          {d.sales_by_product.map((row) => (
            <li key={row.product_name} className="ledger-row">
              <div className="row-main">
                <span className="row-title">{row.product_name}</span>
                <span className="muted small">
                  {row.heads ? `${t.heads(row.heads)} · ` : ''}
                  <Kg value={row.net_kg} /> · {t.avgPrice} {formatAmount(row.avg_price_uzs)}
                </span>
              </div>
              <span className="num">{formatUzs(row.amount_uzs)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>{t.salesByClient}</h2>
        <ul className="ledger">
          {d.sales_by_client.map((row) => (
            <li key={row.client_name} className="ledger-row">
              <div className="row-main">
                <span className="row-title">{row.client_name}</span>
                <span className="muted small">
                  {row.heads ? `${t.heads(row.heads)} · ` : ''}
                  <Kg value={row.net_kg} />
                </span>
              </div>
              <span className="num">{formatUzs(row.amount_uzs)}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
