import useSWR from 'swr'
import { fetcher } from './client'

export function useDashboard() {
  return useSWR('/dashboard/stats', fetcher, { refreshInterval: 30_000 })
}

export function useTimeline() {
  return useSWR('/timeline', fetcher)
}

export function useActivity() {
  return useSWR('/activity', fetcher)
}

export function useDaemonStatus() {
  return useSWR('/daemon-status', fetcher, { refreshInterval: 10_000 })
}

export function useCliLog(afterOffset?: number) {
  const key = afterOffset !== undefined
    ? `/cli-log?after=${afterOffset}`
    : '/cli-log'
  return useSWR(key, fetcher, { refreshInterval: 2_000 })
}

export function usePublished() {
  return useSWR('/published', fetcher)
}

export function useAnalytics() {
  return useSWR('/analytics', fetcher)
}

export function useLogs(category?: string, date?: string) {
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  if (date) params.set('date', date)
  const query = params.toString()
  return useSWR(query ? `/logs?${query}` : '/logs', fetcher)
}

export function useDrafts() {
  return useSWR('/drafts', fetcher)
}

export function useContentCalendar(month: string) {
  return useSWR(month ? `/content-calendar?month=${month}` : null, fetcher)
}

export function useInteractIndex() {
  return useSWR('/interact-index', fetcher)
}

export function useNotifications() {
  return useSWR('/notifications', fetcher)
}

export function useQuota() {
  return useSWR('/quota', fetcher, { refreshInterval: 30_000 })
}

export function useEvolution() {
  return useSWR('/evolution', fetcher)
}

export function useFansProfile() {
  return useSWR('/fans-profile', fetcher)
}

export function useStrategy() {
  return useSWR('/strategy', fetcher)
}

export function useAccounts() {
  return useSWR('/accounts', fetcher)
}
