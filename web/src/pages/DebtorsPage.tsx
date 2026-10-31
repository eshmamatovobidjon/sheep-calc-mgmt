import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { api } from '../api'
import { BackLink, Balance, ErrorState, Loading } from '../components'
import { formatDate, formatUzs } from '../format'
import { useMe } from '../hooks'
import { t } from '../texts'

export function DebtorsPage() {
  const canView = useMe().data?.permissions.includes('view') ?? false
  const debtors = useQuery({ queryKey: ['clients', 'debtors'], queryFn: api.debtors })

  return (
    <>
      <BackLink fallback="/more" />
      {debtors.isPending ? (
        <Loading />
      ) : debtors.isError ? (
        <ErrorState error={debtors.error} onRetry={() => debtors.refetch()} />
      ) : (
        <>
          <article className="card">
            <h1>{t.debtorsTitle}</h1>
            <dl className="facts">
              <dt>{t.totalDebt}</dt>
              <dd className="num balance-debt">{formatUzs(debtors.data.total_debt)}</dd>
              <dt>{t.totalCredit}</dt>
              <dd className="num balance-credit">{formatUzs(debtors.data.total_credit)}</dd>
              <dt>{t.netBalance}</dt>
              <dd className="num">{formatUzs(debtors.data.net)}</dd>
            </dl>
            {canView && (
              <div className="actions">
                <Link className="button secondary" to="/reports?kind=debtors">
                  {t.debtorsReport}
                </Link>
              </div>
            )}
          </article>
          {debtors.data.rows.length === 0 ? (
            <p className="state">{t.noDebtors}</p>
          ) : (
            <ul className="list">
              {debtors.data.rows.map((row) => (
                <li key={row.client_id}>
                  <Link to={`/clients/${row.client_id}`} className="row">
                    <span className="row-main">
                      <span className="row-title">{row.name}</span>
                      <span className="muted small">
                        {t.lastSale}: {formatDate(row.last_sale_date)} · {t.lastPayment}:{' '}
                        {formatDate(row.last_payment_date)}
                      </span>
                    </span>
                    <Balance value={row.balance} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  )
}
