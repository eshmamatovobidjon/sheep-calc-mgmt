import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef } from 'react'
import { api } from './api'

/**
 * Runs one async action at a time. A disabled button alone is not enough: a fast double tap
 * fires both clicks before React re-renders, so the guard must be synchronous.
 */
export function useSingleFlight() {
  const busy = useRef(false)
  return (action: () => Promise<unknown>) => {
    if (busy.current) return
    busy.current = true
    action()
      .catch(() => {}) // errors are shown from the mutation state
      .finally(() => {
        busy.current = false
      })
  }
}

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: api.me, staleTime: 60_000 })
}

export function useCanUpload(): boolean {
  return useMe().data?.permissions.includes('upload') ?? false
}

/** After any client/payment change: refetch everything that shows balances or payments. */
export function useInvalidateMoney() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all(
      ['clients', 'client', 'ledger', 'payments'].map((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    )
}
