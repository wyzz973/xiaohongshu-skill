const BASE_URL = import.meta.env.VITE_API_BASE ?? '/api'

export async function fetchAPI<T = unknown>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const fetcher = (url: string) => fetchAPI(url)
