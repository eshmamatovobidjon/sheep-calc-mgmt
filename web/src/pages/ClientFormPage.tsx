import { useMutation, useQuery } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { api, type ClientInput, errorDetails } from '../api'
import { BackLink, ErrorState, Field, Loading } from '../components'
import { useInvalidateMoney, useSingleFlight } from '../hooks'
import { t } from '../texts'

function ClientForm({ id, initial }: { id: number | null; initial: ClientInput }) {
  const navigate = useNavigate()
  const invalidate = useInvalidateMoney()
  const once = useSingleFlight()
  const [name, setName] = useState(initial.name)
  const [phone, setPhone] = useState(initial.phone ?? '')

  const save = useMutation({
    mutationFn: (input: ClientInput) =>
      id === null ? api.createClient(input) : api.updateClient(id, input),
    onSuccess: async (client) => {
      await invalidate()
      if (id === null) {
        navigate(`/clients/${client.id}`, { replace: true, state: { notice: t.clientSaved } })
      } else {
        navigate(-1)
      }
    },
  })
  const { message, fields } = save.isError ? errorDetails(save.error) : { message: '', fields: {} }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    once(() => save.mutateAsync({ name: name.trim(), phone: phone.trim() || null }))
  }

  return (
    <form className="card form" onSubmit={submit} noValidate>
      <h1>{id === null ? t.newClientTitle : t.editClientTitle}</h1>
      {message && !Object.keys(fields).length && (
        <p className="field-error" role="alert">
          {message}
        </p>
      )}
      <Field label={t.clientName} hint={t.clientNameHint} error={fields.name}>
        <input
          className="input"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={100}
          autoComplete="off"
          required
        />
      </Field>
      <Field label={t.phoneOptional} error={fields.phone}>
        <input
          className="input"
          type="tel"
          inputMode="tel"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          maxLength={32}
        />
      </Field>
      <button type="submit" className="button wide-inline" disabled={save.isPending}>
        {save.isPending ? t.saving : t.save}
      </button>
    </form>
  )
}

export function ClientFormPage() {
  const params = useParams()
  const id = params.id ? Number(params.id) : null
  const existing = useQuery({
    queryKey: ['client', id],
    queryFn: () => api.client(id!),
    enabled: id !== null,
  })

  return (
    <>
      <BackLink />
      {id === null ? (
        <ClientForm id={null} initial={{ name: '', phone: null }} />
      ) : existing.isPending ? (
        <Loading />
      ) : existing.isError ? (
        <ErrorState error={existing.error} onRetry={() => existing.refetch()} />
      ) : (
        <ClientForm id={id} initial={{ name: existing.data.name, phone: existing.data.phone }} />
      )}
    </>
  )
}
