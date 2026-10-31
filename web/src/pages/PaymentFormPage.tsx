import { useMutation, useQuery } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api, type ClientDetail, errorDetails, type PaymentResult } from '../api'
import { ClientPicker } from '../ClientPicker'
import { BackLink, Balance, ErrorState, Field, Loading } from '../components'
import { balanceAfterPayment, digitsOnly, formatAmount, formatDate, formatUzs, todayIso } from '../format'
import { useInvalidateMoney, useSingleFlight } from '../hooks'
import { t } from '../texts'

function PaymentDone({ result }: { result: PaymentResult }) {
  return (
    <div className="card">
      <p className="notice" role="status">
        {t.paymentSaved}
      </p>
      <h1>{result.payment.client_name}</h1>
      <dl className="facts">
        <dt>{t.amount}</dt>
        <dd className="num">{formatUzs(result.payment.amount_uzs)}</dd>
        <dt>{t.method}</dt>
        <dd>{result.payment.method_label}</dd>
        <dt>{t.date}</dt>
        <dd>{formatDate(result.payment.date)}</dd>
      </dl>
      <div className="balance-big">
        <span className="muted small">{t.balance}</span>
        <Balance value={result.balance} />
      </div>
      <div className="actions">
        <Link className="button" to={`/clients/${result.payment.client_id}`} replace>
          {t.toClient}
        </Link>
        <Link className="button secondary" to="/payments" replace>
          {t.paymentsTitle}
        </Link>
      </div>
    </div>
  )
}

function PaymentForm({ client, onChangeClient }: { client: ClientDetail; onChangeClient: () => void }) {
  const invalidate = useInvalidateMoney()
  const once = useSingleFlight()
  const catalog = useQuery({ queryKey: ['catalog'], queryFn: api.catalog, staleTime: Infinity })
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('cash')
  const [date, setDate] = useState(todayIso())
  const [note, setNote] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [amountError, setAmountError] = useState('')

  const save = useMutation({
    mutationFn: api.createPayment,
    onSuccess: () => invalidate(),
    onError: () => setConfirming(false),
  })
  const { message, fields } = save.isError ? errorDetails(save.error) : { message: '', fields: {} }

  if (save.isSuccess) return <PaymentDone result={save.data} />

  const methodLabel = catalog.data?.payment_methods.find((m) => m.value === method)?.label ?? method

  const next = (event: FormEvent) => {
    event.preventDefault()
    if (!amount || amount === '0') {
      setAmountError(t.amountRequired)
      return
    }
    setAmountError('')
    setConfirming(true)
  }

  if (confirming) {
    return (
      <div className="card">
        <h1>{t.confirmTitle}</h1>
        <dl className="facts">
          <dt>{t.chooseClient}</dt>
          <dd>{client.name}</dd>
          <dt>{t.amount}</dt>
          <dd className="num">{formatUzs(amount)}</dd>
          <dt>{t.method}</dt>
          <dd>{methodLabel}</dd>
          <dt>{t.date}</dt>
          <dd>{formatDate(date)}</dd>
          {note.trim() && (
            <>
              <dt>{t.note}</dt>
              <dd>{note.trim()}</dd>
            </>
          )}
        </dl>
        <div className="balance-big">
          <span className="muted small">{t.balanceBefore}</span>
          <Balance value={client.balance} />
        </div>
        <div className="balance-big">
          <span className="muted small">{t.balanceAfterPayment}</span>
          <Balance value={balanceAfterPayment(client.balance, amount)} />
        </div>
        <div className="actions">
          <button
            type="button"
            className="button"
            disabled={save.isPending}
            onClick={() =>
              once(() =>
                save.mutateAsync({
                  client_id: client.id,
                  amount_uzs: amount,
                  method,
                  date,
                  note: note.trim() || null,
                }),
              )
            }
          >
            {save.isPending ? t.saving : t.save}
          </button>
          <button
            type="button"
            className="button secondary"
            disabled={save.isPending}
            onClick={() => setConfirming(false)}
          >
            {t.edit}
          </button>
        </div>
      </div>
    )
  }

  return (
    <form className="card form" onSubmit={next} noValidate>
      <h1>{t.newPaymentTitle}</h1>
      <div className="picked-client">
        <span className="row-title">{client.name}</span>
        <Balance value={client.balance} />
      </div>
      <button type="button" className="link-button" onClick={onChangeClient}>
        {t.changeClient}
      </button>
      {message && (
        <p className="field-error" role="alert">
          {message}
        </p>
      )}
      <Field label={t.amount} error={amountError || fields.amount_uzs}>
        <input
          className="input num"
          inputMode="numeric"
          value={amount ? formatAmount(amount) : ''}
          onChange={(event) => setAmount(digitsOnly(event.target.value))}
          autoFocus
          maxLength={20}
        />
      </Field>
      <Field label={t.method} error={fields.method} group>
        <div className="chips">
          {(catalog.data?.payment_methods ?? []).map((option) => (
            <button
              key={option.value}
              type="button"
              className="chip"
              aria-pressed={method === option.value}
              onClick={() => setMethod(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </Field>
      <Field label={t.date} error={fields.date}>
        <input
          className="input"
          type="date"
          value={date}
          max={todayIso()}
          onChange={(event) => setDate(event.target.value)}
          required
        />
      </Field>
      <Field label={t.note} error={fields.note}>
        <textarea
          className="input"
          rows={2}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          maxLength={500}
        />
      </Field>
      <button type="submit" className="button wide-inline">
        {t.next}
      </button>
    </form>
  )
}

export function PaymentFormPage() {
  const [params, setParams] = useSearchParams()
  const clientId = Number(params.get('client')) || null
  const client = useQuery({
    queryKey: ['client', clientId],
    queryFn: () => api.client(clientId!),
    enabled: clientId !== null,
  })
  const pick = (id: number | null) =>
    setParams(id === null ? {} : { client: String(id) }, { replace: true })

  return (
    <>
      <BackLink fallback="/payments" />
      {clientId === null ? (
        <div className="card form">
          <h1>{t.newPaymentTitle}</h1>
          <ClientPicker onPick={pick} autoFocus />
        </div>
      ) : client.isPending ? (
        <Loading />
      ) : client.isError ? (
        <ErrorState error={client.error} onRetry={() => client.refetch()} />
      ) : (
        <PaymentForm key={clientId} client={client.data} onChangeClient={() => pick(null)} />
      )}
    </>
  )
}
