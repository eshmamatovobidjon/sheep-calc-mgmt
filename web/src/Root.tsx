import { Outlet, ScrollRestoration } from 'react-router'
import { ApiError } from './api'
import { BottomNav, ErrorState, Loading } from './components'
import { useMe } from './hooks'
import { insideTelegram } from './telegram'
import { t } from './texts'

function AccessScreen({ message }: { message: string }) {
  return (
    <main className="page">
      <div className="state" role="alert">
        <h1>{t.accessTitle}</h1>
        {insideTelegram ? (
          <>
            <p>{message}</p>
            <p className="muted">{t.accessReopen}</p>
          </>
        ) : (
          <p>{t.accessOutsideTelegram}</p>
        )}
      </div>
    </main>
  )
}

/** Loads /me before any business query; unapproved users only see the access screen. */
export function Root() {
  const me = useMe()

  if (me.isPending) {
    return (
      <main className="page">
        <Loading />
      </main>
    )
  }
  if (me.isError) {
    if (me.error instanceof ApiError && me.error.isAuth) {
      return <AccessScreen message={me.error.message} />
    }
    return (
      <main className="page">
        <ErrorState error={me.error} onRetry={() => me.refetch()} />
      </main>
    )
  }
  return (
    <>
      <main className="page with-nav">
        <Outlet />
      </main>
      <BottomNav permissions={me.data.permissions} />
      <ScrollRestoration />
    </>
  )
}
