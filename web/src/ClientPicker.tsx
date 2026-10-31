import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from './api'
import { Balance, Field } from './components'
import { t } from './texts'

/** Search field with up to 10 matching clients; calls onPick with the chosen client. */
export function ClientPicker({
  onPick,
  autoFocus = false,
}: {
  onPick: (id: number, name: string) => void
  autoFocus?: boolean
}) {
  const [query, setQuery] = useState('')
  const q = query.trim()
  const matches = useQuery({
    queryKey: ['clients', q, 'all', 'picker'],
    queryFn: () => api.clients({ q, filter: 'all', offset: 0, limit: 10 }),
    enabled: q.length >= 2,
  })
  return (
    <>
      <Field label={t.chooseClient} hint={t.chooseClientHint}>
        <input
          className="input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoFocus={autoFocus}
        />
      </Field>
      {matches.data && (
        <ul className="list picker">
          {matches.data.items.length === 0 ? (
            <li className="muted state">{t.noMatches}</li>
          ) : (
            matches.data.items.map((client) => (
              <li key={client.id}>
                <button
                  type="button"
                  className="row"
                  onClick={() => onPick(client.id, client.name)}
                >
                  <span className="row-title">{client.name}</span>
                  <Balance value={client.balance} />
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </>
  )
}
