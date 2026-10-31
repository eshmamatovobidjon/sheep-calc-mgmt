import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, errorDetails, type User, type UserUpdate } from '../api'
import { BackLink, ErrorState, Loading } from '../components'
import { useMe, useSingleFlight } from '../hooks'
import { t } from '../texts'

function UserCard({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const once = useSingleFlight()
  const [confirmBlock, setConfirmBlock] = useState(false)
  const update = useMutation({
    mutationFn: (change: UserUpdate) => api.updateUser(user.id, change),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })
  const apply = (change: UserUpdate) => {
    setConfirmBlock(false)
    once(() => update.mutateAsync(change))
  }
  const busy = update.isPending

  return (
    <li className="card user-card">
      <div className="picked-client">
        <span className="row-main">
          <span className="row-title">{user.full_name}</span>
          <span className="muted small">
            {user.username ? `@${user.username} · ` : ''}
            {user.telegram_id}
          </span>
        </span>
        <span className={`status status-${user.status}`}>{user.status_label}</span>
      </div>

      {update.isError && (
        <p className="field-error" role="alert">
          {errorDetails(update.error).message}
        </p>
      )}

      {user.status === 'pending' ? (
        <>
          <p className="muted small">{t.approveAs}:</p>
          <div className="actions">
            <button type="button" className="button" disabled={busy} onClick={() => apply({ can_upload: true })}>
              {t.approveUpload}
            </button>
            <button type="button" className="button" disabled={busy} onClick={() => apply({ can_view: true })}>
              {t.approveView}
            </button>
            <button
              type="button"
              className="button"
              disabled={busy}
              onClick={() => apply({ can_upload: true, can_view: true })}
            >
              {t.approveBoth}
            </button>
            <button
              type="button"
              className="button danger"
              disabled={busy}
              onClick={() => apply({ status: 'blocked' })}
            >
              {t.reject}
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="chips" role="group" aria-label={t.permissions}>
            <button
              type="button"
              className="chip"
              aria-pressed={user.can_upload}
              disabled={busy}
              onClick={() => apply({ can_upload: !user.can_upload })}
            >
              {t.permUpload}
            </button>
            <button
              type="button"
              className="chip"
              aria-pressed={user.can_view}
              disabled={busy}
              onClick={() => apply({ can_view: !user.can_view })}
            >
              {t.permView}
            </button>
          </div>
          {user.status === 'blocked' ? (
            <button
              type="button"
              className="link-button"
              disabled={busy}
              onClick={() => apply({ status: 'active' })}
            >
              {t.unblock}
            </button>
          ) : confirmBlock ? (
            <div className="confirm">
              <span>{t.blockConfirm}</span>
              <div className="actions">
                <button
                  type="button"
                  className="button danger"
                  disabled={busy}
                  onClick={() => apply({ status: 'blocked' })}
                >
                  {t.yes}
                </button>
                <button type="button" className="button secondary" onClick={() => setConfirmBlock(false)}>
                  {t.no}
                </button>
              </div>
            </div>
          ) : (
            <button type="button" className="link-button danger-text" onClick={() => setConfirmBlock(true)}>
              {t.block}
            </button>
          )}
        </>
      )}
    </li>
  )
}

export function UsersPage() {
  const isAdmin = useMe().data?.permissions.includes('admin') ?? false
  const users = useQuery({ queryKey: ['users'], queryFn: api.users, enabled: isAdmin })

  return (
    <>
      <BackLink fallback="/more" />
      <header className="page-header">
        <h1>{t.usersTitle}</h1>
      </header>
      {!isAdmin ? (
        <p className="state">{t.adminOnly}</p>
      ) : users.isPending ? (
        <Loading />
      ) : users.isError ? (
        <ErrorState error={users.error} onRetry={() => users.refetch()} />
      ) : users.data.length === 0 ? (
        <p className="state">{t.noUsers}</p>
      ) : (
        <ul className="user-list">
          {users.data.map((user) => (
            <UserCard key={user.id} user={user} />
          ))}
        </ul>
      )}
    </>
  )
}
