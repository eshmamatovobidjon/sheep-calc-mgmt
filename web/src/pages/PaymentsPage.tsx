import { useInfiniteQuery, useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { api, errorDetails, type Payment } from '../api'
import { ErrorState, Loading } from '../components'
import { formatDate, formatUzs } from '../format'
import { useInvalidateMoney, useSingleFlight } from '../hooks'
import { t } from '../texts'

const PAGE_SIZE = 50

function PaymentRow({ payment }: { payment: Payment }) {
  const invalidate = useInvalidateMoney()
  const once = useSingleFlight()
  const [confirming, setConfirming] = useState(false)
  const remove = useMutation({
    mutationFn: () => api.deletePayment(payment.id),
    onSuccess: () => invalidate(),
  })

  return (
    <li className="payment-row">
      <div className="row">
        <span className="row-main">
          <Link to={`/clients/${payment.client_id}`} className="row-title">
            {payment.client_name}
          </Link>
          <span className="muted small">
            {formatDate(payment.date)} · {payment.method_label} · {t.enteredBy}:{' '}
            {payment.entered_by}
            {payment.note ? ` · ${payment.note}` : ''}
          </span>
        </span>
        <span className="num balance-credit">{formatUzs(payment.amount_uzs)}</span>
      </div>
      {remove.isError && (
        <p className="field-error inset" role="alert">
          {errorDetails(remove.error).message}
        </p>
      )}
      {confirming ? (
        <div className="confirm inset">
          <span>{t.deleteConfirm}</span>
          <div className="actions">
            <button
              type="button"
              className="button danger"
              disabled={remove.isPending}
              onClick={() => once(() => remove.mutateAsync())}
            >
              {remove.isPending ? t.saving : t.yes}
            </button>
            <button
              type="button"
              className="button secondary"
              disabled={remove.isPending}
              onClick={() => setConfirming(false)}
            >
              {t.no}
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="link-button danger-text inset" onClick={() => setConfirming(true)}>
          {t.delete}
        </button>
      )}
    </li>
  )
}

export function PaymentsPage() {
  const payments = useInfiniteQuery({
    queryKey: ['payments', 'recent'],
    queryFn: ({ pageParam }) => api.payments({ offset: pageParam, limit: PAGE_SIZE }),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0)
      return loaded < last.total ? loaded : undefined
    },
  })
  const items = payments.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <>
      <header className="page-header">
        <div className="header-row">
          <h1>{t.paymentsTitle}</h1>
          <Link className="button small-button" to="/payments/new">
            {t.addPayment}
          </Link>
        </div>
      </header>
      {payments.isPending ? (
        <Loading />
      ) : payments.isError ? (
        <ErrorState error={payments.error} onRetry={() => payments.refetch()} />
      ) : items.length === 0 ? (
        <p className="state">{t.noPayments}</p>
      ) : (
        <>
          <ul className="list">
            {items.map((payment) => (
              <PaymentRow key={payment.id} payment={payment} />
            ))}
          </ul>
          {payments.hasNextPage && (
            <button
              type="button"
              className="button wide"
              disabled={payments.isFetchingNextPage}
              onClick={() => payments.fetchNextPage()}
            >
              {payments.isFetchingNextPage ? t.loading : t.showMore}
            </button>
          )}
        </>
      )}
    </>
  )
}
