"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  Flame,
  RefreshCw,
  Search,
  Download,
  X,
  Filter,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type TrendItem, type VelocityItem } from "@/lib/api"
import { PLATFORM_CONFIG, getPlatformMeta } from "@/lib/platform-config"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatHeat(score: number | null): string {
  if (score === null) return "\u2014"
  if (score >= 1_000_000) return `${(score / 1_000_000).toFixed(1)}M`
  if (score >= 1_000) return `${(score / 1_000).toFixed(0)}K`
  return String(score)
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function downloadCSV(items: TrendItem[], velocityMap: Record<string, VelocityItem>, platform: string) {
  const header = "Platform,Keyword,Rank,Heat Score,Velocity(%),Acceleration,Collected At,URL"
  const rows = items.map((item, i) => {
    const vel = velocityMap[`${platform}:${item.keyword}`]
    return [
      platform,
      `"${item.keyword.replace(/"/g, '""')}"`,
      i + 1,
      item.heat_score ?? "",
      vel?.velocity ?? "",
      vel?.acceleration ?? "",
      item.collected_at,
      item.url ?? "",
    ].join(",")
  })
  const csv = [header, ...rows].join("\n")
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `trends_${platform}_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// VelocityBadge
// ---------------------------------------------------------------------------

function VelocityBadge({ velocity, acceleration }: { velocity: number | null; acceleration: number | null }) {
  if (velocity === null || velocity === 0) {
    return (
      <span className="flex items-center gap-0.5 text-xs text-muted-foreground w-16 justify-end" title="velocity: 0%">
        <Minus className="w-3 h-3" />
        <span className="font-mono">0%</span>
      </span>
    )
  }

  const isUp = velocity > 0
  const Icon = isUp ? TrendingUp : TrendingDown
  const color = isUp ? "text-red-500" : "text-green-600"
  const absVal = Math.abs(velocity)
  const display = absVal >= 100 ? `${Math.round(absVal)}%` : `${absVal.toFixed(1)}%`

  let accelIndicator = ""
  if (acceleration !== null) {
    if (acceleration > 5) accelIndicator = " \u2191\u2191"
    else if (acceleration < -5) accelIndicator = " \u2193\u2193"
  }

  const title = `velocity: ${isUp ? "+" : ""}${velocity.toFixed(1)}%${acceleration !== null ? `, accel: ${acceleration.toFixed(1)}` : ""}`

  return (
    <span className={`flex items-center gap-0.5 text-xs font-mono w-16 justify-end ${color}`} title={title}>
      <Icon className="w-3 h-3 shrink-0" />
      <span>{isUp ? "+" : "-"}{display}{accelIndicator}</span>
    </span>
  )
}

// ---------------------------------------------------------------------------
// Cross-platform comparison panel
// ---------------------------------------------------------------------------

function CrossPlatformPanel({
  keyword,
  allItems,
  velocityMap,
  onClose,
}: {
  keyword: string
  allItems: Record<string, TrendItem[]>
  velocityMap: Record<string, VelocityItem>
  onClose: () => void
}) {
  const matches: { platform: string; item: TrendItem; vel?: VelocityItem }[] = []
  for (const [platform, items] of Object.entries(allItems)) {
    const found = items.find((it) => it.keyword === keyword)
    if (found) {
      matches.push({ platform, item: found, vel: velocityMap[`${platform}:${keyword}`] })
    }
  }

  return (
    <Card className="border-blue-200 bg-blue-50/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          <span>跨平台对比: {keyword}</span>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-6 w-6 p-0">
            <X className="w-4 h-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {matches.length === 0 ? (
          <p className="text-sm text-muted-foreground">该关键词在当前数据中未找到</p>
        ) : (
          <div className="space-y-2">
            {matches.map(({ platform, item, vel }) => {
              const meta = getPlatformMeta(platform)
              return (
                <div key={platform} className="flex items-center gap-3 text-sm">
                  <span
                    className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: meta.color }}
                  />
                  <span className="w-24 truncate font-medium">{meta.displayName}</span>
                  <span className="text-muted-foreground font-mono w-12 text-right">
                    {formatHeat(item.heat_score)}
                  </span>
                  <VelocityBadge velocity={vel?.velocity ?? null} acceleration={vel?.acceleration ?? null} />
                  <span className="text-xs text-muted-foreground">{formatTime(item.collected_at)}</span>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// TrendRow + Skeleton
// ---------------------------------------------------------------------------

function TrendRow({
  item,
  index,
  velocityData,
  onKeywordClick,
}: {
  item: TrendItem
  index: number
  velocityData?: VelocityItem
  onKeywordClick: (keyword: string) => void
}) {
  const rankDisplay = index + 1
  const isHot = rankDisplay <= 3

  return (
    <div className="flex items-center gap-3 py-2.5 border-b last:border-0 hover:bg-muted/30 transition-colors px-3">
      <span
        className={`w-6 text-center text-sm font-bold shrink-0 ${
          rankDisplay === 1
            ? "text-red-500"
            : rankDisplay === 2
              ? "text-orange-400"
              : rankDisplay === 3
                ? "text-yellow-500"
                : "text-muted-foreground"
        }`}
      >
        {rankDisplay}
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          {isHot && <Flame className="w-3 h-3 text-red-400 shrink-0" />}
          <button
            className="text-sm truncate hover:text-blue-600 hover:underline text-left"
            onClick={() => onKeywordClick(item.keyword)}
            title="点击查看跨平台对比"
          >
            {item.keyword}
          </button>
        </div>
        <span className="text-xs text-muted-foreground">{formatTime(item.collected_at)}</span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {item.relevance_label && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${
              item.relevance_label === "relevant"
                ? "bg-green-100 text-green-700"
                : "bg-gray-100 text-gray-400"
            }`}
            title={`相关性: ${item.relevance_score ?? "—"}`}
          >
            {item.relevance_label === "relevant" ? "相关" : "无关"}
          </span>
        )}
        <VelocityBadge
          velocity={velocityData?.velocity ?? null}
          acceleration={velocityData?.acceleration ?? null}
        />
        <span className="text-xs font-mono text-muted-foreground w-12 text-right">
          {formatHeat(item.heat_score)}
        </span>
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        ) : (
          <span className="w-3.5" />
        )}
      </div>
    </div>
  )
}

function TrendRowSkeleton() {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b last:border-0 px-3">
      <Skeleton className="w-6 h-4 shrink-0" />
      <div className="flex-1 space-y-1">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-3 w-20" />
      </div>
      <Skeleton className="w-16 h-4" />
      <Skeleton className="w-12 h-4" />
    </div>
  )
}

// ---------------------------------------------------------------------------
// PlatformCard
// ---------------------------------------------------------------------------

function PlatformCard({
  slug,
  refreshKey,
  velocityMap,
  searchQuery,
  relevantOnly,
  onItemsLoaded,
  onKeywordClick,
}: {
  slug: string
  refreshKey: number
  velocityMap: Record<string, VelocityItem>
  searchQuery: string
  relevantOnly: boolean
  onItemsLoaded: (platform: string, items: TrendItem[]) => void
  onKeywordClick: (keyword: string) => void
}) {
  const [items, setItems] = useState<TrendItem[]>([])
  const [loading, setLoading] = useState(true)
  const meta = getPlatformMeta(slug)

  useEffect(() => {
    let cancelled = false
    api.trends
      .list(1, 50, slug, relevantOnly)
      .then((res) => {
        if (!cancelled) {
          setItems(res.items)
          onItemsLoaded(slug, res.items)
        }
      })
      .catch(() => { if (!cancelled) { setItems([]); onItemsLoaded(slug, []) } })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true; setLoading(true) }
  }, [slug, refreshKey, relevantOnly]) // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = useMemo(() => {
    if (!searchQuery) return items
    const q = searchQuery.toLowerCase()
    return items.filter((it) => it.keyword.toLowerCase().includes(q))
  }, [items, searchQuery])

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2 shrink-0">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <span
            className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: meta.color }}
          />
          {meta.displayName}
          {!loading && (
            <span className="text-xs font-normal text-muted-foreground ml-auto flex items-center gap-2">
              {searchQuery && filtered.length !== items.length && (
                <span>{filtered.length}/{items.length}</span>
              )}
              {!searchQuery && <span>{items.length} 条</span>}
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                title="导出 CSV"
                onClick={() => downloadCSV(filtered, velocityMap, slug)}
              >
                <Download className="w-3.5 h-3.5" />
              </Button>
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 flex-1 overflow-hidden">
        <div className="h-[600px] overflow-y-auto">
          {loading ? (
            Array.from({ length: 12 }).map((_, i) => <TrendRowSkeleton key={i} />)
          ) : filtered.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
              {searchQuery ? (
                <>
                  <Search className="w-8 h-8 opacity-20" />
                  <p className="text-sm">无匹配结果</p>
                </>
              ) : (
                <>
                  <TrendingUp className="w-8 h-8 opacity-20" />
                  <p className="text-sm">暂无近24小时数据</p>
                </>
              )}
            </div>
          ) : (
            filtered.map((item, i) => (
              <TrendRow
                key={`${item.keyword}-${i}`}
                item={item}
                index={i}
                velocityData={velocityMap[`${slug}:${item.keyword}`]}
                onKeywordClick={onKeywordClick}
              />
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

const ALL_PLATFORMS = Object.keys(PLATFORM_CONFIG)

export default function TrendsPage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [velocityMap, setVelocityMap] = useState<Record<string, VelocityItem>>({})
  const [searchQuery, setSearchQuery] = useState("")
  const [activePlatform, setActivePlatform] = useState<string | null>(null)
  const [compareKeyword, setCompareKeyword] = useState<string | null>(null)
  const [allItems, setAllItems] = useState<Record<string, TrendItem[]>>({})
  const [relevantOnly, setRelevantOnly] = useState(true)
  const [enabledPlatforms, setEnabledPlatforms] = useState<string[]>(ALL_PLATFORMS)

  useEffect(() => {
    api.system
      .config()
      .then((cfg) => {
        if (cfg.platforms) {
          const enabled = Object.entries(cfg.platforms)
            .filter(([, v]) => v)
            .map(([k]) => k)
          setEnabledPlatforms(enabled)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    api.trends
      .velocity(undefined, 24, 200)
      .then((res) => {
        const map: Record<string, VelocityItem> = {}
        for (const item of res.items) {
          map[`${item.platform}:${item.keyword}`] = item
        }
        setVelocityMap(map)
      })
      .catch(() => setVelocityMap({}))
  }, [refreshKey])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await api.post("/api/v1/collector/run", {})
      setRefreshKey((k) => k + 1)
    } finally {
      setRefreshing(false)
    }
  }, [])

  const handleItemsLoaded = useCallback((platform: string, items: TrendItem[]) => {
    setAllItems((prev) => ({ ...prev, [platform]: items }))
  }, [])

  const handleKeywordClick = useCallback((keyword: string) => {
    setCompareKeyword((prev) => (prev === keyword ? null : keyword))
  }, [])

  const visiblePlatforms = activePlatform ? [activePlatform] : enabledPlatforms

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TrendingUp className="w-6 h-6" />
            趋势列表
          </h1>
          <p className="text-muted-foreground text-sm mt-1">近24小时各平台热词 Top 50</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          立即采集
        </Button>
      </div>

      {/* Search + Platform Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="搜索关键词..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
          {searchQuery && (
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              onClick={() => setSearchQuery("")}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <Button
          variant={relevantOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setRelevantOnly((v) => !v)}
          className="gap-1.5 shrink-0"
          title="AI 智能过滤：只显示与你相关的趋势"
        >
          <Filter className="w-3.5 h-3.5" />
          {relevantOnly ? "已过滤" : "智能过滤"}
        </Button>
        <div className="flex gap-2 flex-wrap">
          <Badge
            variant={activePlatform === null ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setActivePlatform(null)}
          >
            全部
          </Badge>
          {enabledPlatforms.map((slug) => {
            const meta = getPlatformMeta(slug)
            return (
              <Badge
                key={slug}
                variant={activePlatform === slug ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setActivePlatform(activePlatform === slug ? null : slug)}
              >
                <span
                  className="inline-block w-2 h-2 rounded-full mr-1"
                  style={{ backgroundColor: meta.color }}
                />
                {meta.displayName}
              </Badge>
            )
          })}
        </div>
      </div>

      {/* Cross-platform comparison */}
      {compareKeyword && (
        <CrossPlatformPanel
          keyword={compareKeyword}
          allItems={allItems}
          velocityMap={velocityMap}
          onClose={() => setCompareKeyword(null)}
        />
      )}

      {/* Platform Cards */}
      <div className={`grid grid-cols-1 gap-6 ${activePlatform ? "" : "lg:grid-cols-2 xl:grid-cols-3"}`}>
        {visiblePlatforms.map((slug) => (
          <PlatformCard
            key={slug}
            slug={slug}
            refreshKey={refreshKey}
            velocityMap={velocityMap}
            searchQuery={searchQuery}
            relevantOnly={relevantOnly}
            onItemsLoaded={handleItemsLoaded}
            onKeywordClick={handleKeywordClick}
          />
        ))}
      </div>
    </div>
  )
}
