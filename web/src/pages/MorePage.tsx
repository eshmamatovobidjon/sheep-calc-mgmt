import { Link } from 'react-router'
import { useMe } from '../hooks'
import { t } from '../texts'

export function MorePage() {
  const permissions = useMe().data?.permissions ?? []
  const items = [
    { to: '/debtors', label: t.debtorsTitle, show: true },
    { to: '/reports', label: t.reportsTitle, show: permissions.includes('view') },
    { to: '/users', label: t.usersTitle, show: permissions.includes('admin') },
  ].filter((item) => item.show)

  return (
    <>
      <header className="page-header">
        <h1>{t.moreTitle}</h1>
      </header>
      <ul className="list">
        {items.map((item) => (
          <li key={item.to}>
            <Link to={item.to} className="row">
              <span className="row-title">{item.label}</span>
              <span className="muted">›</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  )
}
