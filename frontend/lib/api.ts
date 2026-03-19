const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`)
  }

  const json = await res.json()
  return json as T
}

export interface HealthStatus {
  status: string
  version: string
}

export interface TrendItem {
  platform: string
  keyword: string
  rank: number | null
  heat_score: number | null
  url: string | null
  collected_at: string
}

export interface TrendsListResponse {
  total: number
  page: number
  page_size: number
  items: TrendItem[]
}

export interface TopTrendItem {
  keyword: string
  platforms: string[]
  max_heat_score: number | null
  latest_collected_at: string
  convergence_score: number
}

export interface TopTrendsResponse {
  items: TopTrendItem[]
}

export interface PlatformTrendItem {
  keyword: string
  rank: number | null
  heat_score: number | null
  url: string | null
  collected_at: string
  convergence_score: number
}

export interface TopByPlatformResponse {
  platforms: Record<string, PlatformTrendItem[]>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  health: () => request<HealthStatus>("/health"),
  trends: {
    list: (page = 1, pageSize = 20) =>
      request<TrendsListResponse>(`/api/v1/trends?page=${page}&page_size=${pageSize}`),
    top: (limit = 20) =>
      request<TopTrendsResponse>(`/api/v1/trends/top?limit=${limit}`),
    topByPlatform: (limit = 10) =>
      request<TopByPlatformResponse>(`/api/v1/trends/top-by-platform?limit=${limit}`),
  },
}
