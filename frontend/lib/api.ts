const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    cache: "no-store",
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
  relevance_score: number | null
  relevance_label: string | null
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

export interface OpportunityAngle {
  angle: string
  idea: string
}

export interface DeepAnalysisContent {
  summary: string
  key_facts: string[]
  background: string
  opportunities: OpportunityAngle[]
  risk: string
  action: string
  sentiment: "positive" | "negative" | "neutral"
}

export interface DeepAnalysisResponse {
  id: number
  keyword: string
  deep_analysis: DeepAnalysisContent
  source_urls: string[]
  search_results_count: number
  analysis_type: string | null
  model: string | null
  created_at: string | null
  cached: boolean
}

export interface BriefResponse {
  id: number
  date: string
  content: string
  model: string | null
  created_at: string
}

export interface SystemConfig {
  ai: { provider: string; configured: boolean }
  tiktok: { configured: boolean }
  scheduler: { collect_cron: string }
  email: { configured: boolean; smtp_host: string; recipient: string | null }
  deep_analysis: { show_business: boolean }
  platforms: Record<string, boolean>
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

export interface TrendsCountResponse {
  total: number
}

export interface VelocityItem {
  platform: string
  keyword: string
  heat_score: number
  rank: number | null
  velocity: number | null
  acceleration: number | null
}

export interface VelocityResponse {
  items: VelocityItem[]
}

export interface SignalItem {
  id: number
  signal_type: "rank_jump" | "new_entry" | "heat_surge"
  platform: string
  keyword: string
  description: string
  value: number | null
  ai_summary: string | null
  detected_at: string
}

export interface SignalListResponse {
  items: SignalItem[]
  total: number
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  health: () => request<HealthStatus>("/health"),
  ai: {
    deepAnalyze: (keyword: string) =>
      request<DeepAnalysisResponse>("/api/v1/ai/deep-analyze", {
        method: "POST",
        body: JSON.stringify({ keyword }),
      }),
    listDeepAnalyses: () =>
      request<DeepAnalysisResponse[]>("/api/v1/ai/deep-analyses"),
    latestBrief: () => request<BriefResponse>("/api/v1/ai/brief/latest"),
    generateBrief: () =>
      request<BriefResponse>("/api/v1/ai/brief", { method: "POST" }),
  },
  scheduler: {
    status: () => request<SchedulerStatus>("/api/v1/scheduler/status"),
  },
  system: {
    config: () => request<SystemConfig>("/api/v1/system/config"),
    setShowBusiness: (show: boolean) =>
      request<{ show_business: boolean }>("/api/v1/system/deep-analysis-mode", {
        method: "PUT",
        body: JSON.stringify({ show }),
      }),
    togglePlatform: (platform: string, enabled: boolean) =>
      request<{ platform: string; enabled: boolean }>("/api/v1/system/platforms", {
        method: "PUT",
        body: JSON.stringify({ platform, enabled }),
      }),
  },
  signals: {
    recent: (hours = 24, limit = 50) =>
      request<SignalListResponse>(`/api/v1/signals/recent?hours=${hours}&limit=${limit}`),
  },
  trends: {
    list: (page = 1, pageSize = 20, platform?: string, relevantOnly = false) => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
      if (platform) params.set("platform", platform)
      if (relevantOnly) params.set("relevant_only", "true")
      return request<TrendsListResponse>(`/api/v1/trends?${params}`)
    },
    top: (limit = 20) => request<TopTrendsResponse>(`/api/v1/trends/top?limit=${limit}`),
    topByPlatform: (limit = 10) =>
      request<TopByPlatformResponse>(`/api/v1/trends/top-by-platform?limit=${limit}`),
    velocity: (platform?: string, hours = 24, limit = 50) => {
      const params = new URLSearchParams({ hours: String(hours), limit: String(limit) })
      if (platform) params.set("platform", platform)
      return request<VelocityResponse>(`/api/v1/trends/velocity?${params}`)
    },
    count: () => request<TrendsCountResponse>("/api/v1/trends/count"),
    clearAll: () => request<TrendsClearResponse>("/api/v1/trends/all", { method: "DELETE" }),
  },
}
