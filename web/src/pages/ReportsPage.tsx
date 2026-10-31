import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import {
  api,
  errorDetails,
  type ReportFormat,
  type ReportKind,
  type ReportRequest,
} from '../api'
import { ClientPicker } from '../ClientPicker'
import { BackLink, Field } from '../components'
import { formatDate, lastMonth, thisMonth, todayIso } from '../format'
import { useMe, useSingleFlight } from '../hooks'
import { t } from '../texts'

type Period = 'all' | 'this' | 'last' | 'custom'

const KINDS: { value: ReportKind; label: string }[] = [
  { value: 'statement', label: t.reportStatement },
  { value: 'trip', label: t.reportTrip },
  { value: 'debtors', label: t.reportDebtors },
]

const PERIODS: { value: Period; label: string }[] = [
  { value: 'all', label: t.periodAll },
  { value: 'this', label: t.periodThisMonth },
  { value: 'last', label: t.periodLastMonth },
  { value: 'custom', label: t.periodCustom },
]

function Chips<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="chips">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className="chip"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export function ReportsPage() {
  const [params] = useSearchParams()
  const canView = useMe().data?.permissions.includes('view') ?? false
  const once = useSingleFlight()
  const initialKind = KINDS.find((k) => k.value === params.get('kind'))?.value ?? 'statement'
  const [kind, setKind] = useState<ReportKind>(initialKind)
  const [format, setFormat] = useState<ReportFormat>('pdf')
  const [client, setClient] = useState<{ id: number; name: string } | null>(null)
  const [tripNumber, setTripNumber] = useState(params.get('number') ?? '')
  const [period, setPeriod] = useState<Period>('all')
  const [from, setFrom] = useState(thisMonth()[0])
  const [to, setTo] = useState(todayIso())
  const [message, setMessage] = useState('')

  const trips = useQuery({
    queryKey: ['trips', 'options'],
    queryFn: () => api.trips({ offset: 0, limit: 100 }),
    enabled: kind === 'trip',
  })

  const build = (): ReportRequest | null => {
    if (kind === 'debtors') return { kind, format }
    if (kind === 'trip') return tripNumber ? { kind, format, number: Number(tripNumber) } : null
    if (!client) return null
    const range =
      period === 'this' ? thisMonth() : period === 'last' ? lastMonth() : period === 'custom' ? [from, to] : null
    return { kind, format, client_id: client.id, date_from: range?.[0], date_to: range?.[1] }
  }
  const report = build()

  const sendReport = useMutation({
    mutationFn: api.sendReport,
    onSuccess: (result) => setMessage(t.sent(result.filename)),
  })
  const downloadReport = useMutation({ mutationFn: api.downloadReport })
  const busy = sendReport.isPending || downloadReport.isPending
  const failed = sendReport.error ?? downloadReport.error

  const run = (action: 'send' | 'download') => {
    if (!report) return
    setMessage('')
    sendReport.reset()
    downloadReport.reset()
    once(() => (action === 'send' ? sendReport : downloadReport).mutateAsync(report))
  }

  if (!canView) {
    return (
      <>
        <BackLink fallback="/more" />
        <p className="state">{t.noReportAccess}</p>
      </>
    )
  }

  return (
    <>
      <BackLink fallback="/more" />
      <div className="card form">
        <h1>{t.reportsTitle}</h1>
        <Field label={t.reportKind} group>
          <Chips options={KINDS} value={kind} onChange={setKind} />
        </Field>

        {kind === 'statement' &&
          (client ? (
            <div className="picked-client">
              <span className="row-title">{client.name}</span>
              <button type="button" className="link-button" onClick={() => setClient(null)}>
                {t.changeClient}
              </button>
            </div>
          ) : (
            <ClientPicker onPick={(id, name) => setClient({ id, name })} />
          ))}

        {kind === 'statement' && (
          <Field label={t.period} group>
            <Chips options={PERIODS} value={period} onChange={setPeriod} />
          </Field>
        )}
        {kind === 'statement' && period === 'custom' && (
          <div className="date-range">
            <Field label={t.dateFrom}>
              <input className="input" type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
            </Field>
            <Field label={t.dateTo}>
              <input className="input" type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} />
            </Field>
          </div>
        )}

        {kind === 'trip' && (
          <Field label={t.tripLabel}>
            <select className="input" value={tripNumber} onChange={(e) => setTripNumber(e.target.value)}>
              <option value="">{t.chooseTrip}</option>
              {trips.data?.items.map((trip) => (
                <option key={trip.number} value={trip.number}>
                  {t.tripNumber(trip.number)} · {formatDate(trip.departure_date)}
                </option>
              ))}
            </select>
          </Field>
        )}

        <Field label={t.format} group>
          <Chips
            options={[
              { value: 'pdf', label: 'PDF' },
              { value: 'xlsx', label: 'Excel' },
            ]}
            value={format}
            onChange={setFormat}
          />
        </Field>

        {message && (
          <p className="notice" role="status">
            {message}
          </p>
        )}
        {failed && (
          <p className="field-error" role="alert">
            {errorDetails(failed).message}
          </p>
        )}

        <div className="actions">
          <button type="button" className="button" disabled={!report || busy} onClick={() => run('send')}>
            {sendReport.isPending ? t.preparing : t.sendToChat}
          </button>
          <button
            type="button"
            className="button secondary"
            disabled={!report || busy}
            onClick={() => run('download')}
          >
            {downloadReport.isPending ? t.preparing : t.download}
          </button>
        </div>
        <p className="muted small">{t.downloadHint}</p>
      </div>
    </>
  )
}
