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

export interface HeatmapResponse {
  platforms: string[]
  time_slots: string[]
  data: number[][]
  max_heat: number
}

export interface AnalyzeResult {
  id: number
  keyword: string
  business_insight: string
  sentiment: "positive" | "negative" | "neutral"
  related_keywords: string[]
  model: string | null
  created_at: string
}

export interface BriefResponse {
  id: number
  date: string
  content: string
  model: string | null
  created_at: string
}

export interface AlertRule {
  id: number
  keyword: string
  threshold: number
  notify_email: string | null
  is_active: boolean
  created_at: string
}

export interface AlertRulesResponse {
  items: AlertRule[]
}

export interface SystemConfig {
  ai: { provider: string; configured: boolean }
  email: { configured: boolean; smtp_host: string; smtp_port: number; notify_email: string | null }
  tiktok: { configured: boolean }
  scheduler: { collect_cron: string }
}

export interface SchedulerStatus {
  running: boolean
  jobs: { id: string; name: string; next_run_time: string | null; trigger: string }[]
}

export interface CollectorRunResponse {
  status: string
  records_count: number
  platforms: { platform: string; count: number; error: string | null }[]
}

export interface TrendsClearResponse {
  deleted: number
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  health: () => request<HealthStatus>("/health"),
  ai: {
    analyze: (keyword: string) =>
      request<AnalyzeResult>("/api/v1/ai/analyze", {
        method: "POST",
        body: JSON.stringify({ keyword }),
      }),
    latestBrief: () => request<BriefResponse>("/api/v1/ai/brief/latest"),
    generateBrief: () =>
      request<BriefResponse>("/api/v1/ai/brief", { method: "POST" }),
  },
  alerts: {
    listRules: () => request<AlertRulesResponse>("/api/v1/alerts/keywords"),
    createRule: (keyword: string, threshold: number, notify_email: string) =>
      request<AlertRule>("/api/v1/alerts/keywords", {
        method: "POST",
        body: JSON.stringify({ keyword, threshold, notify_email }),
      }),
  },
  scheduler: {
    status: () => request<SchedulerStatus>("/api/v1/scheduler/status"),
  },
  system: {
    config: () => request<SystemConfig>("/api/v1/system/config"),
  },
  trends: {
    list: (page = 1, pageSize = 20) =>
      request<TrendsListResponse>(`/api/v1/trends?page=${page}&page_size=${pageSize}`),
    top: (limit = 20) => request<TopTrendsResponse>(`/api/v1/trends/top?limit=${limit}`),
    topByPlatform: (limit = 10) =>
      request<TopByPlatformResponse>(`/api/v1/trends/top-by-platform?limit=${limit}`),
    clearAll: () => request<TrendsClearResponse>("/api/v1/trends/all", { method: "DELETE" }),
  },
}
