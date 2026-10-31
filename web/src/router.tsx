import { Navigate, createBrowserRouter } from 'react-router'
import { ClientFormPage } from './pages/ClientFormPage'
import { ClientPage } from './pages/ClientPage'
import { ClientsPage } from './pages/ClientsPage'
import { DebtorsPage } from './pages/DebtorsPage'
import { MorePage } from './pages/MorePage'
import { PaymentFormPage } from './pages/PaymentFormPage'
import { PaymentsPage } from './pages/PaymentsPage'
import { ReportsPage } from './pages/ReportsPage'
import { TripPage } from './pages/TripPage'
import { TripsPage } from './pages/TripsPage'
import { UsersPage } from './pages/UsersPage'
import { Root } from './Root'

export const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { index: true, element: <Navigate to="/clients" replace /> },
      { path: 'clients', element: <ClientsPage /> },
      { path: 'clients/new', element: <ClientFormPage /> },
      { path: 'clients/:id', element: <ClientPage /> },
      { path: 'clients/:id/edit', element: <ClientFormPage /> },
      { path: 'payments', element: <PaymentsPage /> },
      { path: 'payments/new', element: <PaymentFormPage /> },
      { path: 'trips', element: <TripsPage /> },
      { path: 'trips/:number', element: <TripPage /> },
      { path: 'more', element: <MorePage /> },
      { path: 'debtors', element: <DebtorsPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'users', element: <UsersPage /> },
      { path: '*', element: <Navigate to="/clients" replace /> },
    ],
  },
])
