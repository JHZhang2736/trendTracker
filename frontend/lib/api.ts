const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  })

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`)
  }

  const json: ApiResponse<T> = await res.json()
  return json.data ?? (json as T)
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

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  health: () => request<HealthStatus>("/health"),
  trends: {
    list: (page = 1, pageSize = 20) =>
      request<TrendsListResponse>(`/api/v1/trends?page=${page}&page_size=${pageSize}`),
  },
}
