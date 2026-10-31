import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { api, type LedgerLine } from '../api'
import { BackLink, Balance, ErrorState, Loading, Notice } from '../components'
import { formatAmount, formatDate, formatUzs } from '../format'
import { useCanUpload } from '../hooks'
import { t } from '../texts'

function LedgerRow({ line }: { line: LedgerLine }) {
  const shipment = line.kind === 'shipment'
  const details = shipment
    ? [
        line.trip_number !== null ? t.trip(line.trip_number) : null,
        line.product,
        line.heads ? t.heads(line.heads) : null,
        line.net_kg ? `${formatAmount(line.net_kg)} ${t.kg}` : null,
      ]
    : [line.payment_method]
  return (
    <li className="ledger-row">
      <div className="row-main">
        <span className="row-title">
          {shipment ? t.shipment : t.payment} · {formatDate(line.date)}
        </span>
        <span className="muted small">
          {details.filter(Boolean).join(' · ')}
          {line.note ? ` · ${line.note}` : ''}
        </span>
      </div>
      <div className="ledger-amounts">
        <span className={`num ${shipment ? 'balance-debt' : 'balance-credit'}`}>
          {shipment ? '+' : '−'}
          {formatUzs(line.amount_uzs)}
        </span>
        <span className="muted small num">
          {t.balanceAfter}: {formatAmount(line.running_balance)}
        </span>
      </div>
    </li>
  )
}

export function ClientPage() {
  const id = Number(useParams().id)
  const valid = Number.isInteger(id) && id > 0
  const canUpload = useCanUpload()
  const client = useQuery({
    queryKey: ['client', id],
    queryFn: () => api.client(id),
    enabled: valid,
  })
  const ledger = useQuery({
    queryKey: ['ledger', id],
    queryFn: () => api.ledger(id),
    enabled: valid && client.isSuccess,
  })

  if (!valid) {
    return (
      <>
        <BackLink />
        <p className="state">{t.clientNotFound}</p>
      </>
    )
  }

  return (
    <>
      <BackLink />
      <Notice />
      {client.isPending ? (
        <Loading />
      ) : client.isError ? (
        <ErrorState error={client.error} onRetry={() => client.refetch()} />
      ) : (
        <>
          <article className="card">
            <h1>{client.data.name}</h1>
            {client.data.phone && (
              <p className="muted">
                {t.phone}: <a href={`tel:${client.data.phone}`}>{client.data.phone}</a>
              </p>
            )}
            <div className="balance-big">
              <span className="muted small">{t.balance}</span>
              <Balance value={client.data.balance} />
            </div>
            <dl className="facts">
              <dt>{t.shipped}</dt>
              <dd className="num">{formatUzs(client.data.shipped)}</dd>
              <dt>{t.paid}</dt>
              <dd className="num">{formatUzs(client.data.paid)}</dd>
              <dt>{t.lastSaleDate}</dt>
              <dd>{formatDate(client.data.last_sale_date)}</dd>
              <dt>{t.lastPaymentDate}</dt>
              <dd>{formatDate(client.data.last_payment_date)}</dd>
            </dl>
            {canUpload && (
              <div className="actions">
                <Link className="button" to={`/payments/new?client=${id}`}>
                  {t.addPayment}
                </Link>
                <Link className="button secondary" to={`/clients/${id}/edit`}>
                  {t.edit}
                </Link>
              </div>
            )}
          </article>

          <section className="card">
            <h2>{t.ledgerTitle}</h2>
            {ledger.isPending ? (
              <Loading />
            ) : ledger.isError ? (
              <ErrorState error={ledger.error} onRetry={() => ledger.refetch()} />
            ) : ledger.data.lines.length === 0 ? (
              <p className="muted">{t.ledgerEmpty}</p>
            ) : (
              <ul className="ledger">
                {/* Newest first; running balance is computed oldest-first on the server. */}
                {[...ledger.data.lines].reverse().map((line, index) => (
                  <LedgerRow key={index} line={line} />
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </>
  )
}
