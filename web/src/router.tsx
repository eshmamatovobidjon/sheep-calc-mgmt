import { Navigate, createBrowserRouter } from 'react-router'
import { ClientFormPage } from './pages/ClientFormPage'
import { ClientPage } from './pages/ClientPage'
import { ClientsPage } from './pages/ClientsPage'
import { PaymentFormPage } from './pages/PaymentFormPage'
import { PaymentsPage } from './pages/PaymentsPage'
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
      { path: '*', element: <Navigate to="/clients" replace /> },
    ],
  },
])
